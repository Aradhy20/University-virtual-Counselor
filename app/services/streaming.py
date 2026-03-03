"""
Streaming Service — Sentence-Level Response Streaming

Splits AI responses into sentence-level chunks for faster TTS delivery.
Instead of waiting for the full response, each sentence is sent to TTS
as soon as it's ready.

Phase 4 Upgrade:
  - Sentence boundary detection for Hindi/English/Hinglish
  - Streaming generator compatible with ElevenLabs TTS
  - Reduced time-to-first-byte for voice responses
"""
import re
import logging
from typing import AsyncGenerator

logger = logging.getLogger("aditi.streaming")


# Sentence boundary regex — handles Hindi (।), English (. ! ?), and mixed
SENTENCE_BOUNDARY = re.compile(
    r'(?<=[.!?।])\s+|(?<=[.!?।])(?=[A-Z\u0900-\u097F])'
)

# Minimum sentence length (avoid sending tiny fragments)
MIN_SENTENCE_LENGTH = 15


def split_into_sentences(text: str) -> list[str]:
    """
    Split response text into sentence-level chunks.
    
    Handles:
      - English periods, exclamation, question marks
      - Hindi purna viram (।)
      - Hinglish mixed text
      - Removes <think>...</think> blocks from Text-to-Speech output
      - Preserves short responses as single chunk
    
    Returns list of sentences, each suitable for independent TTS.
    """
    if not text:
        return []

    # Step 1: Strip internal analytical reasoning before speaking
    # This prevents TTS from vocalizing the AI's internal thoughts
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    if len(text.strip()) < MIN_SENTENCE_LENGTH:
        return [text.strip()] if text and text.strip() else []

    # Split by sentence boundaries
    raw_sentences = SENTENCE_BOUNDARY.split(text.strip())
    
    # Merge tiny fragments with previous sentence
    sentences = []
    buffer = ""
    
    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        
        if buffer:
            candidate = buffer + " " + s
        else:
            candidate = s
        
        if len(candidate) >= MIN_SENTENCE_LENGTH:
            sentences.append(candidate)
            buffer = ""
        else:
            buffer = candidate
    
    # Don't lose the buffer
    if buffer:
        if sentences:
            sentences[-1] = sentences[-1] + " " + buffer
        else:
            sentences.append(buffer)
    
    return sentences


async def stream_sentences(text: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields sentences one at a time.
    
    Usage:
        async for sentence in stream_sentences(response_text):
            async for audio in voice.text_to_speech_stream(sentence):
                send_to_twilio(audio)
    """
    sentences = split_into_sentences(text)
    for sentence in sentences:
        yield sentence


def estimate_speech_duration_ms(text: str) -> int:
    """
    Estimate how long it takes to speak a sentence (in milliseconds).
    Average speaking rate: ~150 words/minute = ~2.5 words/second.
    
    Used for silence detection timing.
    """
    word_count = len(text.split())
    return int((word_count / 2.5) * 1000)
