"""
Voice Service — ElevenLabs (Primary) + Deepgram Aura (Fallback)

Features:
  - ElevenLabs with eleven_multilingual_v2 model for Hindi/English/Hinglish
  - Custom voice design for "Aditi" — warm Indian female counselor
  - Deepgram Aura fallback (aura-asteria-en)
  - PCM→Mulaw transcoding for Twilio
  - Consistent voice maintained across entire call
"""
import os
import io
import struct
import audioop
import logging
import json
from dotenv import load_dotenv
from deepgram import DeepgramClient
from elevenlabs.client import AsyncElevenLabs
from app.services.config_loader import config_loader

load_dotenv()
logger = logging.getLogger("aditi.voice")


# ElevenLabs Voice Configuration for Aditi
# Using Voice Design to create the perfect Indian counselor voice
ADITI_VOICE_DESIGN = {
    "name": "Aditi - TMU Counselor",
    "description": "A warm, confident Indian female voice. Sounds like a caring elder sister who is a senior university admission counselor. Professional yet approachable. Speaks naturally in Hindi, English, and Hinglish. Age: 28-35. Accent: Indian English with natural Hindi inflections.",
    "labels": {
        "accent": "indian",
        "age": "young_adult",
        "gender": "female",
        "use_case": "customer_support"
    }
}

# Primary: Standard Voice (Works on Free Plan)
ADITI_PRIMARY_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Rachel

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
        self.aditi_voice_id = None

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
            self._setup_aditi_voice()
        else:
            logger.warning("ElevenLabs API Key missing. Using Deepgram TTS only.")
            self.eleven = None

    def _setup_aditi_voice(self):
        """
        Set up the Aditi voice ID from Config.
        """
        config = config_loader.get_config()
        self.aditi_voice_id = config.voice.voice_id
        logger.info(f"Aditi voice ID set to: {self.aditi_voice_id}")

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
        voice_id = config.voice.voice_id or self.aditi_voice_id
        
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

        voice_id = self.aditi_voice_id or "21m00Tcm4TlvDq8ikWAM"
        
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

    def text_to_speech_stream_pcm(self, text: str):
        """Alternative: PCM output with manual Mulaw conversion."""
        if not self.eleven:
            return

        voice_id = self.aditi_voice_id or "21m00Tcm4TlvDq8ikWAM"

        try:
            audio_iterator = self.eleven.text_to_speech.stream(
                voice_id=voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="pcm_8000",
                optimize_streaming_latency=4,
            )

            for pcm_chunk in audio_iterator:
                if pcm_chunk:
                    mulaw_chunk = audioop.lin2ulaw(pcm_chunk, 2)
                    yield mulaw_chunk

        except Exception as e:
            logger.error(f"TTS (PCM path) failed: {e}", exc_info=True)

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
