"""
TMU Admission Counselor AI — Main Application
FastAPI server with Twilio WebSocket voice streaming.

SDK versions targeted:
  - Deepgram SDK v5.3.x  (listen.v2.connect)
  - ElevenLabs SDK v2.34  (text_to_speech.stream)
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import json
import base64
import asyncio
from datetime import datetime
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

# Import Services
# from app.services.rag import RAGService
from app.services.rag_native import RAGServiceNative as RAGService
from app.services.llm_router import LLMRouter
from app.services.voice import VoiceService
from app.services.cache import CacheService
from app.tools.memory import SessionMemory
from app.tools.leads import save_lead
from app.core.database import init_db
from app.services.hallucination_guard import check_response, check_response_length
from app.services.emotional_tracker import EmotionalTracker
from app.services.streaming import split_into_sentences, estimate_speech_duration_ms
from app.services.config_loader import config_loader

# Load Env
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("riya")


# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Initializing database tables...")
    init_db()
    logger.info("TMU Admission Counselor AI is ready.")
    yield
    logger.info("Shutting down.")


from fastapi.middleware.cors import CORSMiddleware

# Load Admin Router (if available)
try:
    from app.routers.admin import router as admin_router
    from app.routers.campaign import router as campaign_router
    from app.routers.livekit_calls import router as livekit_router
    from app.routers.dashboard import router as dashboard_router

except ImportError:
    admin_router = None
    campaign_router = None
    livekit_router = None
    dashboard_router = None

# ... (logging setup) ...

app = FastAPI(title="TMU Admission Counselor AI", lifespan=lifespan)

# CORS Configuration for React Dashboard
origins = [
    "http://localhost",
    "http://localhost:5173", # Vite Dev Server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Admin Router
if admin_router:
    app.include_router(admin_router)
if campaign_router:
    app.include_router(campaign_router)
if livekit_router:
    app.include_router(livekit_router)
if dashboard_router:
    app.include_router(dashboard_router)

# Initialize Services
rag_service = RAGService()
llm_router = LLMRouter()
voice_service = VoiceService()
cache_service = CacheService()
session_memory = SessionMemory()


# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------
@app.get("/")
async def health_check():
    return {
        "message": "TMU Admission Counselor AI is running",
        "status": "active",
        "services": {
            "deepgram": voice_service.dg_client is not None,
            "elevenlabs": voice_service.eleven is not None,
            "vector_store": rag_service.vector_store is not None,
        }
    }

# ------------------------------------------------------------------
# API Integration (Text Chat Endpoint)
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: str = "api-test"
    name: str = None
    city: str = None
    course: str = None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard API endpoint for text-based interaction.
    Useful for testing, web widgets, or non-voice channels.
    """
    try:
        from app.services.agent_workflow import run_crew_agent
        
        # Build history string (minimal for API teststateless)
        history_str = "" 
        
        response_data = await run_crew_agent(
            user_input=request.message,
            user_name=request.name,
            user_course=request.course,
            user_city=request.city,
            caller_phone=request.session_id,
            history=history_str,
            turn_count=1
        )
        
        text_response, new_info = response_data
        
        # Safety checks
        clean_response, _, _ = check_response(text_response)
        
        return {
            "response": clean_response,
            "extracted_info": new_info,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"API Chat Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Twilio Voice Webhook
# ------------------------------------------------------------------
@app.post("/voice")
async def voice(request: Request):
    """
    Twilio calls this URL when a phone call starts.
    We respond with TwiML that opens a bidirectional WebSocket stream.
    """
    logger.info("Received /voice webhook from Twilio")
    response = VoiceResponse()
    # No TwiML greeting — the greeting is sent via ElevenLabs through the WebSocket
    # This ensures a SINGLE consistent voice throughout the entire call

    # Tell Twilio to open a WebSocket to our /voice-stream endpoint
    # Extract caller number to pass to WebSocket for lead capture
    form_data = await request.form()
    caller_number = form_data.get("From", "Unknown")
    
    host = request.headers.get("host", request.url.hostname or "localhost:8000")
    ws_url = f"wss://{host}/voice-stream?caller={caller_number}"
    
    logger.info(f"Instructing Twilio to connect WebSocket to: {ws_url}")
    connect = Connect()
    connect.stream(url=ws_url)
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")


# Active call counter for concurrent call monitoring
active_calls = 0
MAX_CONCURRENT_CALLS = 10  # Enforce cap to prevent API quota exhaustion

# ------------------------------------------------------------------
# WebSocket Voice Stream (Deepgram v5 + ElevenLabs Multilingual)
# ------------------------------------------------------------------
@app.websocket("/voice-stream")
async def websocket_endpoint(websocket: WebSocket):
    global active_calls
    await websocket.accept()
    
    # Enforce max concurrent calls
    if active_calls >= MAX_CONCURRENT_CALLS:
        logger.warning(f"Max concurrent calls reached ({MAX_CONCURRENT_CALLS}). Rejecting.")
        await websocket.close(code=1013, reason="Server busy")
        return
    
    active_calls += 1
    logger.info(f"WebSocket connection accepted from Twilio | Active calls: {active_calls}")

    stream_sid = None
    call_sid = None
    dg_connection = None
    # Queue to pass finalized transcripts from Deepgram callback → processing loop
    response_queue: asyncio.Queue = asyncio.Queue()
    is_speaking = False  # Lock: True while TTS audio is being sent
    speaking_lock = asyncio.Lock()  # Mutex for speaking state
    cancel_speaking = asyncio.Event()  # Signal to cancel current TTS
    
    # Utterance buffering: collect fragments before processing
    utterance_buffer = []  # List of transcript fragments
    utterance_timer: asyncio.Task | None = None  # Timer task for silence detection
    UTTERANCE_SILENCE_MS = 200  # Wait 0.2s of silence before processing (was 400ms)

    
    # Response deduplication
    last_response_text = ""
    last_response_time = 0
    
    # Phase 4: Emotional intelligence tracker
    emotion_tracker = EmotionalTracker()
    silence_timer_task: asyncio.Task | None = None
    SILENCE_TIMEOUT_S = 8  # Seconds of silence before nudge
    
    # Session state for lead capture
    caller_phone = websocket.query_params.get("caller", "Unknown")
    lead_state = {
        "name": None,
        "course": None,
        "city": None,
        "phone": caller_phone,
        "saved": False
    }
    
    # Conversation history for context (prevents repeated greetings)
    conversation_turns = []  # list of ("USER"/"RIYA", text) tuples
    turn_count = 0  # Tracks how many exchanges have happened (for lead capture timing)

    try:
        # ----------------------------------------------------------
        # 1. Connect to Deepgram Live STT (SDK v5)
        # ----------------------------------------------------------
        dg_socket = None

        # ----------------------------------------------------------
        # 1. Connect to Deepgram Live STT (Manual WebSocket)
        # ----------------------------------------------------------
        if voice_service.dg_api_key:
            try:
                import websockets
                
                # Direct URL construction ensures correct params
                # encoding=linear16 because we do manual conversion from Mulaw
                # Direct URL construction ensures correct params
                # encoding=mulaw — send Twilio's audio directly!
                # endpointing=200ms for faster response
                dg_url = (
                    "wss://api.deepgram.com/v1/listen"
                    "?model=nova-2"
                    "&language=multi"          # Supports English + Hindi simultaneously
                    "&encoding=mulaw"
                    "&sample_rate=8000"
                    "&interim_results=true"
                    "&endpointing=250"         # Detect end-of-speech faster (was 300ms)
                    "&smart_format=true"
                    "&no_delay=true"           # Lower latency mode
                )

                
                extra_headers = {
                    "Authorization": f"Token {voice_service.dg_api_key}"
                }
                
                logger.info(f"Connecting to Deepgram manually: {dg_url}")
                dg_socket = await websockets.connect(dg_url, additional_headers=extra_headers)
                logger.info("Deepgram (manual) connected!")

                # Receiver task with utterance buffering
                async def flush_utterance_buffer():
                    """Flush accumulated utterance fragments to the response queue."""
                    nonlocal utterance_buffer, utterance_timer
                    if utterance_buffer:
                        complete_utterance = " ".join(utterance_buffer).strip()
                        utterance_buffer = []
                        if complete_utterance and len(complete_utterance) > 1:
                            logger.info(f"[USER COMPLETE]: {complete_utterance}")
                            await response_queue.put(complete_utterance)
                    utterance_timer = None

                async def schedule_utterance_flush():
                    """Wait for silence period, then flush buffer."""
                    await asyncio.sleep(UTTERANCE_SILENCE_MS / 1000.0)
                    await flush_utterance_buffer()

                async def dg_receiver():
                    nonlocal utterance_buffer, utterance_timer
                    try:
                        async for msg in dg_socket:
                            try:
                                res = json.loads(msg)
                                msg_type = res.get('type', 'unknown')
                                
                                if msg_type == 'Metadata':
                                    logger.info(f"Deepgram Metadata: model={res.get('model_info', {}).get('name', '?')}")
                                elif msg_type == 'UtteranceEnd':
                                    # Deepgram's own utterance end signal — flush immediately
                                    logger.debug("Deepgram: UtteranceEnd — flushing buffer")
                                    if utterance_timer:
                                        utterance_timer.cancel()
                                        utterance_timer = None
                                    await flush_utterance_buffer()
                                elif msg_type == 'error':
                                    logger.error(f"Deepgram error: {res}")
                                
                                # Handle transcripts
                                channel = res.get('channel')
                                if channel and isinstance(channel, dict):
                                    alternatives = channel.get('alternatives', [])
                                    if alternatives and isinstance(alternatives, list) and len(alternatives) > 0:
                                        alt = alternatives[0]
                                        transcript = alt.get('transcript', '') if isinstance(alt, dict) else ''
                                        is_final = res.get('is_final', False)
                                        speech_final = res.get('speech_final', False)
                                        
                                        if transcript and is_final:
                                            logger.info(f"[STT fragment]: {transcript} (speech_final={speech_final})")
                                            
                                            # Barge-in: if AI is speaking and user starts talking
                                            if is_speaking and stream_sid:
                                                logger.info("🔇 BARGE-IN detected — clearing audio")
                                                cancel_speaking.set()  # Signal TTS to stop
                                                try:
                                                    await websocket.send_text(json.dumps({
                                                        "event": "clear",
                                                        "streamSid": stream_sid
                                                    }))
                                                except: pass
                                            
                                            # Add to utterance buffer
                                            utterance_buffer.append(transcript)
                                            
                                            # If Deepgram says speech is final, flush immediately
                                            if speech_final:
                                                if utterance_timer:
                                                    utterance_timer.cancel()
                                                await flush_utterance_buffer()
                                            else:
                                                # Reset silence timer
                                                if utterance_timer:
                                                    utterance_timer.cancel()
                                                utterance_timer = asyncio.create_task(schedule_utterance_flush())

                            except Exception as e:
                                logger.error(f"Deepgram msg processing error: {e}")
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("Deepgram socket closed")
                    except Exception as e:
                        logger.error(f"Deepgram receiver error: {e}")

                # Start receiver in background
                asyncio.create_task(dg_receiver())

            except Exception as e:
                logger.error(f"Deepgram connection failed: {e}", exc_info=True)
                dg_socket = None

        # ----------------------------------------------------------
        # 2. Background task: process user messages from the queue
        # ----------------------------------------------------------
        async def silence_watchdog():
            """Phase 4: Detect prolonged silence and send nudge."""
            nonlocal is_speaking, stream_sid
            try:
                await asyncio.sleep(SILENCE_TIMEOUT_S)
                # User has been silent for too long
                silence_count = emotion_tracker.register_silence()
                nudge = emotion_tracker.get_silence_nudge()
                if nudge and stream_sid and not is_speaking:
                    logger.info(f"Silence nudge #{silence_count}: {nudge}")
                    is_speaking = True
                    try:
                        provider = voice_service.get_tts_provider()
                        if provider == "elevenlabs":
                            tts_stream = voice_service.text_to_speech_stream(nudge)
                        else:
                            tts_stream = voice_service.deepgram_tts_stream(nudge)
                        async for audio_chunk in tts_stream:
                            if cancel_speaking.is_set():
                                break
                            if audio_chunk and stream_sid:
                                payload = base64.b64encode(audio_chunk).decode("utf-8")
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": payload}
                                })
                    except Exception as e:
                        logger.error(f"Silence nudge TTS error: {e}")
                    finally:
                        is_speaking = False
            except asyncio.CancelledError:
                pass

        def reset_silence_timer():
            """Reset the silence watchdog timer."""
            nonlocal silence_timer_task
            if silence_timer_task:
                silence_timer_task.cancel()
            silence_timer_task = asyncio.create_task(silence_watchdog())

        async def process_loop():
            nonlocal is_speaking, turn_count, last_response_text, last_response_time
            consecutive_errors = 0  # Track repeated 'I can't hear you' failures
            MAX_CONSECUTIVE_ERRORS = 2  # After 2 fails, switch to a graceful hold message
            while True:
                text = await response_queue.get()
                if text is None:
                    break  # Poison pill — shutdown

                # Discard extremely short noise (single characters or empty)
                if len(text.strip()) <= 1:
                    logger.info(f"Discarding empty or noise transcript: '{text}'")
                    continue

                try:
                    # Reset silence timer (user spoke)
                    reset_silence_timer()
                    
                    # Phase 4: Update emotional state
                    mood = await emotion_tracker.async_update(text)
                    mood_hint = emotion_tracker.get_response_hint()
                    
                    # Reset cancel signal for new response
                    cancel_speaking.clear()

                    # Check cache first (fast path)
                    cached = cache_service.check_static_response(text)
                    if cached:
                        response_text = cached
                    else:
                        # Process via CrewAI multi-agent workflow
                        from app.services.agent_workflow import run_crew_agent as run_agent

                        # Hard timeout: 5s max for LLM
                        try:
                            # Build history string from recent turns (last 10)
                            history_str = ""
                            if conversation_turns:
                                recent = conversation_turns[-10:]
                                history_str = "\n".join(
                                    f"{role}: {msg}" for role, msg in recent
                                )
                            
                            response_payload = await asyncio.wait_for(
                                run_agent(
                                    text,
                                    lead_state["name"],
                                    lead_state["course"],
                                    lead_state["city"],
                                    caller_phone=caller_phone,
                                    history=history_str,
                                    turn_count=turn_count,
                                    mood_hint=emotion_tracker.get_response_hint()
                                ),
                                timeout=15.0
                            )
                            # Unpack response (text, extracted_data)
                            response_text, new_info = response_payload
                            
                            # Update lead state if we got new info
                            if new_info:
                                if new_info.get("name"): lead_state["name"] = new_info["name"]
                                if new_info.get("course"): lead_state["course"] = new_info["course"]
                                if new_info.get("city"): lead_state["city"] = new_info["city"]
                                
                                logger.info(f"Lead State: {lead_state}")
                                
                                # Check if ready to save (and hasn't been saved yet)
                                if (lead_state["name"] and lead_state["course"] 
                                    and lead_state["city"] and not lead_state["saved"]):
                                    
                                    saved = save_lead(
                                        name=lead_state["name"],
                                        phone=caller_phone or "Unknown",
                                        course=lead_state["course"],
                                        city=lead_state["city"]
                                    )
                                    if saved:
                                        lead_state["saved"] = True
                                        logger.info("Lead saved to Excel!")

                        except asyncio.TimeoutError:
                            response_text = "One moment please, let me check that for you."
                            logger.warning("LLM timeout — using fallback response")

                    # 🛡️ HALLUCINATION GUARD: Check response before sending
                    response_text, was_modified, violations = check_response(response_text)
                    if was_modified:
                        logger.warning(f"Hallucination guard triggered: {violations}")
                    
                    # Enforce response length for voice
                    response_text = check_response_length(response_text, max_words=60)
                    
                    logger.info(f"[AI]: {response_text[:80]}...")
                    
                    # Deduplication: skip if same response sent within 5 seconds
                    import time
                    now_ts = time.time()
                    if response_text == last_response_text and (now_ts - last_response_time) < 5.0:
                        logger.warning(f"Skipping duplicate response within 5s")
                        consecutive_errors += 1
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            # Break the "I can't hear you" loop gracefully
                            consecutive_errors = 0
                            response_text = "I'm so sorry, it seems there may be a brief network issue. Please hold on for just a moment and try speaking again — I'm right here!"
                            logger.warning("Breaking error loop with graceful recovery message")
                        else:
                            continue
                    else:
                        consecutive_errors = 0  # Reset on a successful unique response
                    last_response_text = response_text
                    last_response_time = now_ts

                    # Track conversation turns for history context
                    conversation_turns.append(("STUDENT", text))
                    conversation_turns.append(("ADITI", response_text))
                    turn_count += 1

                    # Save to persistent cross-session memory using their phone number
                    if caller_phone and caller_phone != "Unknown":
                        session_memory.add_user_message(caller_phone, text)
                        session_memory.add_ai_message(caller_phone, response_text)

                    # Phase 4: Sentence-level streaming TTS
                    is_speaking = True
                    cancel_speaking.clear()
                    
                    # Get mood-aware TTS settings
                    tts_mood_settings = emotion_tracker.get_tts_settings()
                    
                    # Split response into sentences for streaming
                    sentences = split_into_sentences(response_text)
                    logger.info(f"Streaming {len(sentences)} sentence(s) | mood={emotion_tracker.current_mood}")
                    
                    for sentence in sentences:
                        if cancel_speaking.is_set():
                            logger.info("TTS interrupted by barge-in")
                            break
                        
                        provider = voice_service.get_tts_provider()
                        
                        if provider == "elevenlabs":
                            # ElevenLabs TTS with mood-aware settings
                            try:
                                async for audio_chunk in voice_service.text_to_speech_stream_with_settings(
                                    sentence, voice_settings=tts_mood_settings
                                ):
                                    if cancel_speaking.is_set():
                                        break
                                    if audio_chunk and stream_sid:
                                        payload = base64.b64encode(audio_chunk).decode("utf-8")
                                        await websocket.send_json({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {"payload": payload}
                                        })
                            except Exception as e:
                                logger.error(f"ElevenLabs TTS error: {e}. Falling back to Deepgram.")
                                if not cancel_speaking.is_set():
                                    try:
                                        async for audio_chunk in voice_service.deepgram_tts_stream(sentence):
                                            if cancel_speaking.is_set():
                                                break
                                            if audio_chunk and stream_sid:
                                                payload = base64.b64encode(audio_chunk).decode("utf-8")
                                                await websocket.send_json({
                                                    "event": "media",
                                                    "streamSid": stream_sid,
                                                    "media": {"payload": payload}
                                                })
                                    except Exception as dg_err:
                                        logger.error(f"Deepgram Fallback failed: {dg_err}")
                        else:
                            # Direct Deepgram TTS
                            try:
                                async for audio_chunk in voice_service.deepgram_tts_stream(sentence):
                                    if cancel_speaking.is_set():
                                        break
                                    if audio_chunk and stream_sid:
                                        payload = base64.b64encode(audio_chunk).decode("utf-8")
                                        await websocket.send_json({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {"payload": payload}
                                        })
                            except Exception as dg_err:
                                logger.error(f"Deepgram TTS failed: {dg_err}")
                    
                    is_speaking = False
                    # Reset silence timer after speaking
                    reset_silence_timer()

                except Exception as e:
                    logger.error(f"Process loop error: {e}", exc_info=True)
                    is_speaking = False

        # Start the processing loop as a background task
        process_task = asyncio.create_task(process_loop())

        # ----------------------------------------------------------
        # 3. Main loop: receive Twilio WebSocket messages
        # ----------------------------------------------------------
        chunk_count = 0
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data["event"] == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid")
                logger.info(f"Stream started: {stream_sid} (call: {call_sid})")
                
                # --- PROACTIVE GREETING ---
                # Greeting logic running in background to avoid blocking the loop
                async def send_greeting():
                    nonlocal is_speaking
                    is_speaking = True
                    try:
                        # Dynamic, professional, senior-counselor-style greeting
                        now = datetime.now()
                        hour = now.hour
                        if 5 <= hour < 12:
                            time_greeting = "Good morning"
                        elif 12 <= hour < 17:
                            time_greeting = "Good afternoon"
                        else:
                            time_greeting = "Good evening"

                        # Check memory. If they called before, give a "welcome back"
                        history = session_memory.get_chat_history(caller_phone)
                        
                        if "PREVIOUS" in history:
                            greeting_text = f"{time_greeting} again! Welcome back to TMU. This is Aditi. So glad you called back! English ya Hindi mein baat karein?"
                        else:
                            variations = [
                                f"{time_greeting}! TMU Admissions mein aapka swagat hai. Main Aditi hoon, aapki Senior Counselor. English ya Hindi, kaise baat karein?",
                                f"{time_greeting}! This is Aditi from TMU, Moradabad. So glad you called! English or Hindi, whichever you prefer?",
                                f"Namaste! Aditi here from TMU. I'm here to help you with admissions. English ya Hindi mein baat karein?",
                            ]
                            greeting_text = random.choice(variations)
                            
                        logger.info(f"Generated Greeting: {greeting_text}")

                        provider = voice_service.get_tts_provider()
                        
                        if provider == "elevenlabs":
                            try:
                                logger.info("Sending greeting via ElevenLabs...")
                                async for chunk in voice_service.text_to_speech_stream(greeting_text):
                                    if chunk:
                                        b64_audio = base64.b64encode(chunk).decode("utf-8")
                                        await websocket.send_json({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {"payload": b64_audio}
                                        })
                            except Exception as e:
                                logger.error(f"ElevenLabs Greeting error: {e}. Falling back to Deepgram.")
                                try:
                                    async for chunk in voice_service.deepgram_tts_stream(greeting_text):
                                        if chunk:
                                            b64_audio = base64.b64encode(chunk).decode("utf-8")
                                            await websocket.send_json({
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {"payload": b64_audio}
                                            }) 
                                except Exception as dg_e:
                                    logger.error(f"Deepgram greeting fallback also failed: {dg_e}")
                        else:
                            try:
                                logger.info("Sending greeting via Deepgram...")
                                async for chunk in voice_service.deepgram_tts_stream(greeting_text):
                                    if chunk:
                                        b64_audio = base64.b64encode(chunk).decode("utf-8")
                                        await websocket.send_json({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {"payload": b64_audio}
                                        }) 
                            except Exception as e:
                                logger.error(f"Deepgram Greeting error: {e}")
                    finally:
                        is_speaking = False
                        logger.info("Greeting complete — is_speaking reset to False")

                asyncio.create_task(send_greeting())

            elif data["event"] == "media":
                payload = data["media"]["payload"]
                audio_chunk = base64.b64decode(payload)
                
                # Check for silence (simple energy check) to avoid sending empty noise?
                # For now, send everything to Deepgram.
                
                if dg_socket:
                    # Always send audio to Deepgram for STT processing.
                    # This ensures user speech is captured even during TTS playback
                    # (barge-in detection relies on receiving transcripts).
                    try:
                        await dg_socket.send(audio_chunk)
                    except Exception as ws_err:
                        logger.error(f"Deepgram send error: {ws_err}")
                        dg_socket = None  # Mark as dead so we don't keep trying
                    
                    chunk_count += 1
                    if chunk_count % 100 == 0:
                        logger.info(f"Audio chunks sent to Deepgram: {chunk_count}")

            elif data["event"] == "stop":
                logger.info("Stream stopped by Twilio")
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Cleanup
        if dg_socket:
            try:
                await dg_socket.close()
            except Exception:
                pass
        # Signal process loop to stop
        await response_queue.put(None)
        active_calls = max(0, active_calls - 1)
    
    logger.info(f"Voice session ended | Active calls remaining: {active_calls}")


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
