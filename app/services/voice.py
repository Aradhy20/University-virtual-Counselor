"""
Voice Service — ElevenLabs (Primary) + Deepgram Aura (Fallback)

Features:
  - ElevenLabs with eleven_multilingual_v2 model for Hindi/English/Hinglish
  - Custom voice design for "Riya" — warm Indian female counselor
  - Deepgram Aura fallback (aura-asteria-en)
  - PCM→Mulaw transcoding for Twilio
  - Consistent voice maintained across entire call
"""
import os
import io
import struct
import logging
import json
from dotenv import load_dotenv
from deepgram import DeepgramClient
from elevenlabs.client import AsyncElevenLabs
from app.services.config_loader import config_loader

load_dotenv()
logger = logging.getLogger("riya.voice")


# ElevenLabs Voice Configuration for Riya
# Using Voice Design to create the perfect Indian counselor voice
RIYA_VOICE_DESIGN = {
    "name": "Riya - TMU Counselor",
    "description": "A warm, confident Indian female voice. Sounds like a caring elder sister who is a senior university admission counselor. Professional yet approachable. Speaks naturally in Hindi, English, and Hinglish. Age: 28-35. Accent: Indian English with natural Hindi inflections.",
    "labels": {
        "accent": "indian",
        "age": "young_adult",
        "gender": "female",
        "use_case": "customer_support"
    }
}

# Primary: Standard Voice (Works on Free Plan)
RIYA_PRIMARY_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Rachel

# Fallback: Pre-built Indian female voices from ElevenLabs library
INDIAN_VOICE_IDS = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "jsCqWAovK2LkecY7zXl4",  # Mahi - Conversational, Warm, Clear
    "oWAxZDx7w5VEj9dCyTzz",  # Monika Sogam - Deep, Natural, Friendly
    
]

class VoiceService:
    def __init__(self):
        config = config_loader.get_config()
        self.dg_api_key = config.api.deepgram_api_key or os.getenv("DEEPGRAM_API_KEY")
        self.eleven_api_key = config.api.elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.riya_voice_id = RIYA_PRIMARY_VOICE_ID

        # --- Deepgram (Speech-to-Text + TTS Fallback) ---
        if self.dg_api_key:
            self.dg_client = DeepgramClient(api_key=self.dg_api_key)

            logger.info("Deepgram client initialized (SDK v5)")
        else:
            logger.warning("Deepgram API Key missing.")
            self.dg_client = None

        # --- ElevenLabs (Primary TTS - Async) ---
        if self.eleven_api_key:
            self.eleven = AsyncElevenLabs(api_key=self.eleven_api_key)
            logger.info("ElevenLabs Async client initialized")
            self._setup_riya_voice()
        else:
            logger.warning("ElevenLabs API Key missing. Using Deepgram TTS only.")
            self.eleven = None

    def _setup_riya_voice(self):
        """
        Set up the Riya voice ID from Config.
        """
        config = config_loader.get_config()
        configured_voice_id = (config.voice.voice_id or "").strip()
        if configured_voice_id and not configured_voice_id.startswith("aura-"):
            self.riya_voice_id = configured_voice_id
        else:
            self.riya_voice_id = RIYA_PRIMARY_VOICE_ID
        logger.info(f"Riya voice ID set to: {self.riya_voice_id}")

    def get_tts_provider(self) -> str:
        """
        Prefer ElevenLabs when available because it is the higher-quality primary TTS.
        Fall back to Deepgram automatically if ElevenLabs is unavailable.
        """
        if self.eleven:
            return "elevenlabs"
        return "deepgram"

    def get_deepgram_options(self) -> dict:
        """Deepgram live STT options — multi-language auto-detect."""
        return {
            "model": "nova-2",
            "detect_language": True,
            "smart_format": True,
            "encoding": "mulaw",
            "sample_rate": 8000,
            "channels": 1,
            "interim_results": True,
            "punctuate": True,
            "endpointing": 300,
        }

    # ----------------------------------------------------------
    # ElevenLabs TTS (Primary) — Multilingual
    # ----------------------------------------------------------
    async def text_to_speech_stream(self, text: str):
        """
        ElevenLabs TTS with eleven_multilingual_v2 for Hindi+English.
        Outputs Mulaw 8kHz for Twilio.
        """
        if not self.eleven:
            logger.error("ElevenLabs client not initialized.")
            return

        config = config_loader.get_config()
        voice_id = self.riya_voice_id or RIYA_PRIMARY_VOICE_ID
        
        # Dynamic Settings from Config
        voice_settings = {
            "stability": config.voice.stability,
            "similarity_boost": config.voice.similarity_boost,
            "style": config.voice.style,
            "use_speaker_boost": config.voice.use_speaker_boost,
        }

        try:
            # Async stream generation
            audio_iterator = self.eleven.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="ulaw_8000",
                optimize_streaming_latency=4,
                voice_settings=voice_settings
            )

            async for chunk in audio_iterator:
                if chunk:
                    yield chunk

        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}. Switching to Deepgram...")
            raise  # Re-raise so caller can fall back to Deepgram

    async def text_to_speech_stream_with_settings(self, text: str, voice_settings: dict = None):
        """
        Phase 4: Mood-aware ElevenLabs TTS with dynamic voice settings.
        
        Accepts voice_settings dict with keys:
          - stability (0.0-1.0)
          - similarity_boost (0.0-1.0)  
          - style (0.0-1.0)
        
        Falls back to default settings if none provided.
        """
        if not self.eleven:
            logger.error("ElevenLabs client not initialized.")
            return

        # Ensure we don't pass a Deepgram ID to ElevenLabs
        config = config_loader.get_config()
        voice_id = self.riya_voice_id or RIYA_PRIMARY_VOICE_ID
        
        # Merge with defaults
        settings = {
            "stability": 0.50,
            "similarity_boost": 0.80,
            "style": 0.50,
            "use_speaker_boost": True,
        }
        if voice_settings:
            settings.update(voice_settings)
            settings["use_speaker_boost"] = True  # Always keep speaker boost

        try:
            audio_iterator = self.eleven.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="ulaw_8000",
                optimize_streaming_latency=4,
                voice_settings=settings
            )

            async for chunk in audio_iterator:
                if chunk:
                    yield chunk

        except Exception as e:
            logger.error(f"ElevenLabs Mood TTS failed: {e}")
            raise



    # ----------------------------------------------------------
    # Deepgram TTS (Fallback)
    # ----------------------------------------------------------
    async def deepgram_tts_stream(self, text: str, model: str = "aura-asteria-en"):
        """
        Deepgram Aura TTS — fallback when ElevenLabs is unavailable.
        Returns Mulaw 8kHz audio chunks for Twilio.
        """
        if not self.dg_api_key:
            logger.error("Deepgram API key missing for TTS")
            return

        try:
            import httpx

            url = "https://api.deepgram.com/v1/speak"
            params = {
                "model": model,
                "encoding": "mulaw",
                "sample_rate": "8000",
                "container": "none",
            }
            headers = {
                "Authorization": f"Token {self.dg_api_key}",
                "Content-Type": "application/json",
            }
            body = {"text": text}

            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream("POST", url, params=params, headers=headers, json=body) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=1024):
                        if chunk:
                            yield chunk

        except Exception as e:
            logger.error(f"Deepgram TTS error: {e}", exc_info=True)
