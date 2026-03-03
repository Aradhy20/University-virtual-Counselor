"""
Agent Workflow — Aditi's Brain (Production v4.0 — Bilingual Senior Counselor)

Architecture:
  Layer 1 (Brain):      Intent router (Semantic) + parallel retrieval
  Layer 2 (Knowledge):  Hybrid FAISS/BM25 with probability scoring
  Layer 3 (Persona):    "Aditi" - Senior Counselor, Empathetic, Bilingual
  Layer 4 (Slot-filling): Embedded lead capture (natural, conversational)
  Layer 5 (Safety):     Confidence-based Clarification + Anti-Hallucination
  Layer 6 (Language):   Auto-detects Hindi / Hinglish / English per turn

Improvements (v4.0):
  - Auto language detection: responds in English OR Hindi/Hinglish based on user
  - Human-like senior counselor persona (NOT a chatbot)
  - A.C.E.R. communication model integrated
  - Richer TMU knowledge base from tmu.ac.in
"""
import asyncio
import os
import json
import csv
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from groq import AsyncGroq

# from app.services.rag import RAGService
from app.services.llm_router import LLMRouter
from app.services.sheets import sheet_service
from app.services.rag_native import RAGServiceNative as RAGService
from app.services.query_preprocessor import preprocess_query, dual_search_queries
from app.services.language_detector import detect_language, get_language_instruction
from app.services.config_loader import config_loader
import logging
import random

logger = logging.getLogger("aditi.workflow")


# ------------------------------------------------------------------
# 1. Initialize Services (singleton)
# ------------------------------------------------------------------
rag_service = RAGService()
llm_router = LLMRouter()

# Initialize Native Groq Client
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

# ------------------------------------------------------------------
# 2. System Prompts — Loaded from Config
# ------------------------------------------------------------------
# Default fallback prompts are now in config_loader.py
# We access them via config_loader.get_config().prompts.system_prompt


CHITCHAT_PROMPT = """You are Riya, Senior Admission Counselor at Teerthanker Mahaveer University (TMU), Moradabad.
You are on a LIVE PHONE CALL. Speak warmly and naturally — like a caring elder sister (didi), not a call center robot.

BILINGUAL RULES:
- Default to English. If student speaks Hindi/Hinglish, switch to Hindi/Hinglish immediately and naturally.
- Use warm filler words in English ("Hmm, well...", "Oh, that's great!") or Hindi ("Accha!", "Dekhiye...", "Zaroor!").
- Keep every response MAX 2-3 sentences. You are on a phone call, not writing an essay.

COMMON SCENARIOS (handle naturally):
1. Hello/Hi/Namaste → "Hello! I am Riya, your personal Senior Admission Counselor at TMU. May I ask which course or programme are you looking for?" (Hindi: "Namaste! Main Riya hoon, TMU ki Senior Counselor. Aap kis course ke baare mein jaanna chahte hain?")
2. Thank you / Shukriya → "It is my absolute pleasure, dear! Do call again if you need anything." (Hindi: "Yeh mera farz hai! Phir zaroor call karein agar kuch aur poochna ho.")
3. Bye / Alvida → "It was lovely speaking with you! Wishing you a bright, successful future. Take care!" (Hindi: "Bahut accha laga aapse baat karke! Aapka bhavishya ujjwal ho. Allah Hafiz!")
4. How are you? → "I am wonderful, thank you so much for asking! Now, how may I guide you towards your dream career at TMU today?" (Hindi: "Main bilkul theek hoon, shukriya! Ab batao, main aapke sapno ki career ke liye kya kar sakti hoon?")
5. Are you a robot/AI? → "Not at all! I am Riya, a real Senior Counselor here at TMU. I am here to personally guide you!" (Hindi: "Nahi nahi! Main Riya hoon, ek real counselor TMU mein. Main personally aapki madad ke liye hoon!")
6. One-word replies (OK, Haan, Fine) → Ask the next useful, forward-moving question about their course interest or qualification.

{language_instruction}

HISTORY:
{history}

QUESTION: {question}
RIYA'S RESPONSE (max 2-3 sentences, warm, natural, bilingual):"""

LEAD_CAPTURE_PROMPT = """You are Riya, Senior Admission Counselor.
Goal: Collect student details NATURALLY and sweetly. ONE at a time.

MISSING: {missing_info}
COLLECTED: {collected_info}

STRATEGY:
- Answer their question FIRST, then ask for a missing detail.
- Example: "I'd love to WhatsApp you the brochure! May I have your number?"
- Keep it extremely short (1-2 sentences).

{language_instruction}

HISTORY:
{history}

STUDENT SAID: {question}
RIYA'S RESPONSE:"""

LEAD_EXTRACT_PROMPT = """Extract entities. Return JSON: {{"name": null, "course": null, "city": null}}
Use null if not found.
Input: {question}"""

class LeadInfo(BaseModel):
    name: Optional[str] = Field(description="Student's name")
    course: Optional[str] = Field(description="Course interest")
    city: Optional[str] = Field(description="Student's city")


# ------------------------------------------------------------------
# 3. Fallback Responses (Safe Mode)
# ------------------------------------------------------------------
FALLBACKS = {
    "low_confidence": [
        "That is such a wonderfully specific detail! I want to make absolutely sure I give you the perfect answer, so I'll confirm it and send it to your WhatsApp. Could you share your number with me?",
        "I want to give you 100% accurate information, dear. Let me just quickly check that for you and text you the details. What is your phone number?",
        "That's a great question! Let me verify the latest updates from the university and send them right over to you. What's the best number to reach you on?",
        "I'll confirm this directly with our senior counselors and get back to you right away. May I note down your number for that?"
    ],
    "error": [
        "Oh no, I'm so sorry! The network broke up a little bit just now. Could you please repeat that for me?",
        "I apologize, dear, I couldn't quite hear you due to the network. Could you say that again?",
        "I just missed that last part. Could you please tell me one more time?",
        "I'm so sorry, I couldn't quite catch that. Can you say it once more for me?"
    ],
    "greeting": [
        "Namaste! I am Aditi, your Senior Admission Counselor here at TMU. How can I help make your day better?",
        "Hello there! I'm Aditi from TMU. I'd love to know, which course are you most interested in?",
        "Hi! Welcome to TMU. I am Aditi, and I'm so happy you called! What would you like to know today?"
    ],
    "goodbye": [
        "It was absolutely wonderful speaking with you today! Please do call back if you have any other questions at all. Wishing you all the very best!",
        "Thank you so much for calling! Welcome to the TMU family. I'll make sure to send all the details to your WhatsApp right away.",
        "Thank you for chatting with me! If you have even the smallest confusion, please feel free to call again. Take care and stay happy!"
    ]
}

def _get_fallback(category: str) -> str:
    return random.choice(FALLBACKS.get(category, FALLBACKS["error"]))


# ------------------------------------------------------------------
# 4. Core Logic Functions
# ------------------------------------------------------------------

async def _expand_query(query: str) -> list[str]:
    """
    Deprecated: LLM-assisted query expansion generates 2 search-friendly rewrites.
    This was causing a 1-3 second blocking delay before vector retrieval.
    Now we rely entirely on fast, deterministic string normalization via `dual_search_queries`.
    """
    return []


async def _retrieve_context(query: str) -> Tuple[str, float]:
    """
    Retrieves context with cross-encoder re-ranking and real confidence scoring.
    
    Pipeline:
      1. Generate query variants (original + Hinglish normalized + LLM expanded)
      2. Run hybrid search (FAISS + BM25 + RRF) for each variant
      3. Cross-encoder re-ranks all candidates → real confidence score
    
    Returns: (context_string, confidence_score, source_ids)
    """
    # Defensive check
    if not rag_service:
        return ("(Knowledge base offline. Use general knowledge.)", 0.0, [])

    try:
        # Step 1: Build search queries
        queries = dual_search_queries(query)
        
        # Step 2: Collect candidates from all query variants
        all_docs = []
        seen_content = set()

        for q in queries:
            # RAGServiceNative returns lists of strings
            docs = rag_service.retrieve(q, top_k=3)
            for doc_str in docs:
                content_key = doc_str[:80]
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    all_docs.append(doc_str)

        if not all_docs:
            logger.warning(f"No context found for: {query[:40]}...")
            return ("(No info found)", 0.0, [])

        # Step 3: Cross-encoder re-ranking
        try:
            final_docs, confidence = rag_service.rerank_and_score(query, all_docs, top_k=3)
        except Exception as e:
            logger.warning(f"Re-ranking failed: {e}. Using raw order.")
            final_docs = all_docs[:3]
            confidence = 0.70
            
        context = "\n\n".join(final_docs)
        # We don't have source IDs in the native FAISS implementation right now
        source_ids = ["knowledge_base"]
        logger.info(f"Retrieved {len(final_docs)} chunks (confidence={confidence:.2f}) for: {query[:40]}...")
        return (context, confidence, source_ids)

    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return ("(Error)", 0.0, [])



def _log_missed_query(query: str, score: float):
    """Logs low confidence queries for self-learning."""
    try:
        from pathlib import Path as _P
        _missed = _P(__file__).parent.parent.parent / "data" / "missed_queries.csv"
        _missed.parent.mkdir(parents=True, exist_ok=True)
        file_path = str(_missed)
        # Check if file exists to add header
        header = not os.path.exists(file_path)
        with open(file_path, "a", encoding="utf-8") as f:
            if header:
                f.write("timestamp,query,confidence\n")
            f.write(f"{datetime.now()},{query.replace(',', ' ')},{score}\n")
    except Exception as e:
        logger.error(f"Failed to log missed query: {e}")


async def _rag_respond(query: str, history: str = "", context: str = "", score: float = 0.0,
                      lang: str = "en", mood_hint: str = "") -> str:
    """
    Generates response based on Tiered Confidence Policy + Language-Awareness.
    - Score > 0.85: High Confidence (Authoritative Answer)
    - Score > 0.60: Medium Confidence (Hesitant/Cautious Answer)
    - Score < 0.60: Low Confidence (Clarification / Deferral)
    """
    
    # CONFIDENCE GATING
    config = config_loader.get_config()
    CONFIDENCE_HIGH = 0.85
    CONFIDENCE_MED = 0.60
    
    lang_instruction = get_language_instruction(lang)
    
    # [LOW CONFIDENCE] If context is empty or score is low, trigger clarification
    if score < CONFIDENCE_MED:
        logger.info(f"Low confidence ({score:.2f} < {CONFIDENCE_MED}). Switching to Clarification Mode.")
        _log_missed_query(query, score)
        
        try:
            prompt_text = config.prompts.clarification_prompt.format(
                question=query,
                history=history,
                language_instruction=lang_instruction
            )
            prompt_text += "\n\nBefore speaking, wrap your internal analytical reasoning in <think>...</think> tags. Only output the spoken response outside the tags."
            response = await groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=350,
                temperature=0.6,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return _get_fallback("error")

    # [HIGH/MEDIUM CONFIDENCE] Check the tier to inject behavioral modifiers
    prompt_template = config.prompts.system_prompt
    confidence_modifier = ""
    
    if score >= CONFIDENCE_HIGH:
        confidence_modifier = "You are extremely confident. Deliver the answer authoritatively and warmly without hesitation."
    else:
        # Medium confidence (0.60 - 0.85)
        confidence_modifier = "You are fairly confident but not 100% certain. Start your response with a natural human hesitation like 'Hmm, if I recall correctly...' or 'Let me think, I believe...', but remain sweet and helpful."
    
    try:
        # We append the thinking logic directly to the final prompt block
        prompt_text = prompt_template.format(
            context=context,
            question=query,
            history=history,
            language_instruction=lang_instruction,
            mood_hint=f"MOOD GUIDANCE: {mood_hint}\nCONFIDENCE GUIDANCE: {confidence_modifier}"
        )
        prompt_text += "\n\nCRITICAL INSTRUCTION: Before you output the final spoken response, you MUST wrap your internal logic and reasoning in <think>...</think> tags. The final spoken response must be outside the tags and extremely natural."
        
        response = await groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=500, # Increased max tokens to accommodate thinking block
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"RAG generation failed: {e}")
        return _get_fallback("error")


async def _chitchat_respond(query: str, history: str = "", lang: str = "en") -> str:
    lang_instruction = get_language_instruction(lang)
    prompt_text = CHITCHAT_PROMPT.format(
        question=query,
        history=history,
        language_instruction=lang_instruction
    )
    try:
        response = await groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Chitchat error: {e}")
        return _get_fallback("error")


async def _lead_capture_respond(query: str, history: str, lang: str = "en", **kwargs) -> str:
    collected = []
    missing = []
    
    vals = {
        "Name": kwargs.get("lead_name"),
        "Course": kwargs.get("lead_course"),
        "City": kwargs.get("lead_city")
    }
    
    for k, v in vals.items():
        if v: collected.append(f"{k}: {v}")
        else: missing.append(k)
        
    collected_str = ", ".join(collected) if collected else "Nothing yet"
    missing_str = ", ".join(missing) if missing else "All collected!"
    lang_instruction = get_language_instruction(lang)

    prompt_text = LEAD_CAPTURE_PROMPT.format(
        question=query,
        missing_info=missing_str,
        collected_info=collected_str,
        history=history,
        language_instruction=lang_instruction
    )
    try:
        response = await groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return _get_fallback("error")


async def _extract_lead_info(query: str) -> dict:
    try:
        prompt_text = LEAD_EXTRACT_PROMPT.format(question=query)
        # Force JSON response parsing manually from LlamaIndex output
        response = await groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=150,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result_text = response.choices[0].message.content.strip()
        
        # Clean up markdown JSON block if present
        if result_text.startswith("```json"):
            result_text = result_text[7:-3]
        elif result_text.startswith("```"):
            result_text = result_text[3:-3]
            
        import json
        return json.loads(result_text)
    except Exception as e:
        logger.warning(f"Lead extraction failed: {e}")
        return {}


# ------------------------------------------------------------------
# 5. Main Parallel Pipeline
# ------------------------------------------------------------------

def _check_input_safety(query: str) -> bool:
    """Returns True if input is safe, False if injection detected."""
    config = config_loader.get_config()
    if not config.security.enable_input_safety:
        return True
        
    blocklist = config.security.blocklist
    q_lower = query.lower()
    
    for phrase in blocklist:
        if phrase in q_lower:
            logger.warning(f"Security Alert: Injection attempt detected: {phrase}")
            return False
    return True

async def run_crew_agent(
    user_input: str, 
    user_name: str = None, 
    user_course: str = None, 
    user_city: str = None,
    caller_phone: str = "unknown", 
    history: str = "",
    turn_count: int = 1,
    mood_hint: str = ""
) -> Tuple[str, dict]:
    """
    Parallel Agent V2.1:
    - Parallel Router + Retrieval
    - Dynamic Confidence Handling
    """
    collected_updates = {}
    
    query = preprocess_query(user_input)
    
    # 0. Language Detection (per-turn)
    detected_lang = detect_language(user_input)
    logger.info(f"Detected language: {detected_lang} for: '{user_input[:40]}'")
    
    # 0b. Security Guard
    if not _check_input_safety(query):
        if detected_lang == 'hi':
            return ("Sorry, main sirf TMU admission se related sawaalon ka jawab de sakti hoon. Koi course ke baare mein poochhna tha?", {})
        return ("I'm here to help with TMU admissions only. May I assist you with a specific course or facility?", {})

    try:
        # 1. Fast Route (Zero Latency check)
        fast_intent = llm_router._fast_keyword_route(query)
        
        intent = None
        context = ""
        score = 0.0

        if fast_intent:
            intent = fast_intent
            logger.info(f"Fast intent: {intent}")
        else:
            # 2. Parallel Execution
            intent_task = asyncio.create_task(llm_router.route_query(query))
            context_task = asyncio.create_task(_retrieve_context(query))
            
            try:
                # Wait for both
                results = await asyncio.gather(intent_task, context_task)
                intent = results[0]
                context_data = results[1] # This is now (str, float, list)
                if len(context_data) == 3:
                     context, score, source_ids = context_data
                else:
                     context, score = context_data
                     source_ids = []
                
            except Exception as e:
                logger.error(f"Parallel wait failed: {e}")
                intent = "RAG"
                context = ""
                score = 0.0
                source_ids = []

        # 3. Dispatch
        if intent == "CHITCHAT":
            response = await _chitchat_respond(query, history, lang=detected_lang)
            
        elif intent == "INTERESTED":
            # Extract lead info
            updates = await _extract_lead_info(query)
            if updates:
                collected_updates = {k: v for k, v in updates.items() if v}
                user_name = collected_updates.get("name") or user_name
                user_course = collected_updates.get("course") or user_course
                user_city = collected_updates.get("city") or user_city
                
                # Save to Sheets if we have at least a Name or Course
                if user_name or user_course:
                    sheet_service.add_lead(caller_phone, user_name, user_course, user_city)

            response = await _lead_capture_respond(
                query, history,
                lang=detected_lang,
                lead_name=user_name, lead_course=user_course, lead_city=user_city
            )
            
        else: # RAG
            # If fast routed, we might not have context yet
            if not context and score == 0.0:
                context_data = await _retrieve_context(query)
                if len(context_data) == 3:
                    context, score, source_ids = context_data
                else:
                    context, score = context_data
                    source_ids = []
            
            response = await _rag_respond(query, history, context, score,
                                          lang=detected_lang, mood_hint=mood_hint)


        # 4. Auto-Extraction on RAG turns (Opportunistic)
        if intent == "RAG" and turn_count > 1:
            try:
                auto_updates = await _extract_lead_info(query)
                if auto_updates:
                     for k,v in auto_updates.items():
                         v_str = str(v)
                         if v_str and k not in collected_updates:
                             collected_updates[k] = v_str
            except: pass

        # ------------------------------------------------------------------
        # 5. CONVERSATION LOGGING (Self-Learning Layer 1)
        # ------------------------------------------------------------------
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": f"call_{caller_phone}",
                "query": query,
                "intent": intent,
                "source_ids": source_ids if 'source_ids' in locals() else [],
                "retrieved_context_snippet": context[:200] if context else None,
                "confidence_score": score,
                "response": response,
                "lead_updates": collected_updates
            }
            from pathlib import Path as _P
            _log = _P(__file__).parent.parent.parent / "data" / "conversation_logs.jsonl"
            _log.parent.mkdir(parents=True, exist_ok=True)
            log_path = str(_log)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as log_err:
            logger.error(f"Logging failed: {log_err}")

    except Exception as e:
        logger.error(f"Agent Critical Error: {e}", exc_info=True)
        response = _get_fallback("error")
    
    # 5. CSV LOGGING (User Request)
    try:
        from pathlib import Path as _P
        _csv = _P(__file__).parent.parent.parent / "data" / "conversation_logs.csv"
        _csv.parent.mkdir(parents=True, exist_ok=True)
        csv_path = str(_csv)
        file_exists = os.path.isfile(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "SessionID", "Query", "Response", "Intent", "Confidence"])
            writer.writerow([
                datetime.now().isoformat(),
                f"call_{caller_phone}",
                query,
                response,
                intent if 'intent' in locals() else "Error",
                score if 'score' in locals() else 0.0
            ])
    except Exception as e:
        logger.error(f"CSV logging failed: {e}")

    logger.info(f"Final Response: {response[:50]}...")
    return response, collected_updates
