"""
Emotional Intelligence Tracker — Multi-turn Mood Awareness

Tracks user emotional state across conversation turns.
Adjusts TTS voice settings and response strategy based on mood.

Phase 4 Upgrade:
  - Detect user mood from text cues (frustrated, anxious, excited, neutral)
  - Maintain mood history per session
  - Provide TTS voice parameter adjustments
  - Silence detection nudge timing
"""
import re
import os
import logging
from typing import Optional
from groq import AsyncGroq

logger = logging.getLogger("riya.emotion")


# ----------------------------------------------------------
# Mood Categories
# ----------------------------------------------------------
MOODS = {
    "frustrated": {
        "keywords": [
            r"\b(kya bakwas|time waste|samajh nahi|frustrat|irritat|answer do|seedha bolo|bolo na)",
            r"\b(wrong answer|not helpful|useless|galat|waste|bore|pagal|annoyed)",
            r"\b(baar baar|phir se|already told|nahi samjhe|sun nahi|kab tak)",
        ],
        "tts_settings": {
            "stability": 0.65,        # More stable/calm voice
            "similarity_boost": 0.85,
            "style": 0.30,            # Less expressive, more soothing
        },
        "response_hint": "MOOD: User is frustrated. Be EXTRA patient. Apologize briefly and give a direct, clear answer. Do NOT repeat previous info.",
    },
    "anxious": {
        "keywords": [
            r"\b(tension|worried|stress|darr|nervous|scared|kya hoga|panic|anxious)",
            r"\b(confirm kar do|pakka hai|guarantee|sure hai na|risk|doubt|confused)",
            r"\b(chance milega|ho payega|possible hai|mushkil|difficult)",
        ],
        "tts_settings": {
            "stability": 0.60,
            "similarity_boost": 0.80,
            "style": 0.40,            # Warm, reassuring
        },
        "response_hint": "MOOD: User is anxious. Be extra warm and reassuring. Use: 'Fikr mat kijiye', 'Main guarantee deti hoon', 'Aap bilkul sahi jagah hain'.",
    },
    "excited": {
        "keywords": [
            r"\b(wow|great|amazing|perfect|best|love|excited|super|mast|zabardast)",
            r"\b(bahut accha|too good|excellent|wonderful|awesome|fantastic)",
            r"\b(pakka join|definitely|sure hoon|ready|lena hai|interested hoon)",
        ],
        "tts_settings": {
            "stability": 0.45,
            "similarity_boost": 0.80,
            "style": 0.60,            # More energetic, match their energy
        },
        "response_hint": "MOOD: User is excited! Match their energy, celebrate with them. Use: 'Arre wah!', 'Bahut badiya!', guide toward action NOW.",
    },
    "hesitant": {
        "keywords": [
            r"\b(soch raha|thinking|decide nahi|not sure|confused|dwidha|samajh nahi)",
            r"\b(pata nahi|don.t know|kya karun|options kya|compare|alternative)",
            r"\b(baad mein|later|time chahiye|abhi nahi|sochta hoon|dekhte hain)",
        ],
        "tts_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80,
            "style": 0.45,            # Gentle, patient
        },
        "response_hint": "MOOD: User is hesitant/undecided. Be patient, zero pressure. Offer to share info on WhatsApp. Ask what is holding them back gently.",
    },
    "parent": {
        "keywords": [
            r"\b(mere bete|mere bache|meri beti|my son|my daughter|ward|child)",
            r"\b(parent|father|mother|papa|mummy|guardian|family)",
            r"\b(bachche ke liye|admission karwana|uska future)",
        ],
        "tts_settings": {
            "stability": 0.60,
            "similarity_boost": 0.85,
            "style": 0.35,            # Respectful, formal
        },
        "response_hint": "MOOD: This is a PARENT calling for their child. Be extra respectful, formal. Use 'Aap', 'Ji'. Address their parental concerns about safety, placement, hostel. Reassure them about campus environment.",
    },
    "neutral": {
        "keywords": [],  # Default
        "tts_settings": {
            "stability": 0.50,
            "similarity_boost": 0.80,
            "style": 0.50,
        },
        "response_hint": "",
    },
}


class EmotionalTracker:
    """
    Per-session emotional state tracker.
    
    Usage:
        tracker = EmotionalTracker()
        mood = tracker.update("yeh bahut confusing hai, kuch samajh nahi aa raha")
        tts_settings = tracker.get_tts_settings()
    """

    def __init__(self):
        self.mood_history: list[str] = []
        self.current_mood: str = "neutral"
        self.turn_count: int = 0
        self.silence_count: int = 0  # Consecutive silent turns
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def async_update(self, user_text: str) -> str:
        """
        Analyze user text using LLM and update mood state.
        Returns the current mood.
        """
        self.turn_count += 1
        self.silence_count = 0  # User spoke, reset silence counter

        detected_mood = await self._detect_mood_async(user_text)
        self.mood_history.append(detected_mood)
        
        # Weighted: recent mood matters more, but sustained frustration escalates
        if detected_mood != "neutral":
            self.current_mood = detected_mood
        elif len(self.mood_history) >= 3:
            # If last 3 turns were the same mood, keep it
            recent = self.mood_history[-3:]
            if len(set(recent)) == 1:
                self.current_mood = recent[0]
            else:
                self.current_mood = "neutral"
        
        if self.current_mood != "neutral":
            logger.info(f"Mood detected: {self.current_mood} (turn {self.turn_count})")

        return self.current_mood

    def register_silence(self) -> int:
        """
        Register a silence event. Returns how many consecutive silences.
        """
        self.silence_count += 1
        return self.silence_count

    def get_tts_settings(self) -> dict:
        """
        Get ElevenLabs voice_settings tuned for current mood.
        """
        mood_config = MOODS.get(self.current_mood, MOODS["neutral"])
        return mood_config["tts_settings"]

    def get_response_hint(self) -> str:
        """
        Get a hint string to prepend to the LLM system prompt
        for mood-aware responses.
        """
        mood_config = MOODS.get(self.current_mood, MOODS["neutral"])
        return mood_config.get("response_hint", "")

    def get_silence_nudge(self) -> Optional[str]:
        """
        Get an appropriate nudge message based on silence count.
        Progressive, natural nudges — not robotic.
        """
        if self.silence_count == 1:
            return "Hello, aap wahan hain? Take your time, main sun rahi hoon!"
        elif self.silence_count == 2:
            return "I am still here whenever you are ready. Koi bhi sawaal ho toh zaroor poochiye!"
        elif self.silence_count >= 3:
            return "Lagta hai connection mein thodi dikkat aa rahi hai. Aap dubara call kar sakte hain ya 9568918000 par WhatsApp kijiye — main wahan bhi hoon!"
        return None

    async def _detect_mood_async(self, text: str) -> str:
        """
        Detect mood from text using LLM (zero-shot classification).
        Returns mood category string.
        """
        text_lower = text.lower().strip()
        
        # Skip very short inputs (filler words)
        if len(text_lower) < 3:
            return "neutral"

        try:
            prompt = f"Categorize the user's emotional state based on this text into EXACTLY ONE of the following categories: 'frustrated', 'anxious', 'excited', 'hesitant', 'parent', or 'neutral'. Respond with ONLY the category word.\nUser text: \"{text}\""
            
            response = await self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1,
            )
            detected = response.choices[0].message.content.strip().lower()
            
            # Clean up response just in case the LLM is chatty
            for valid_mood in ["frustrated", "anxious", "excited", "hesitant", "parent", "neutral"]:
                if valid_mood in detected:
                    return valid_mood
            return "neutral"
            
        except Exception as e:
            logger.error(f"LLM Mood detection failed: {e}. Falling back to neutral.")
            return "neutral"

    def get_summary(self) -> dict:
        """
        Get summary of emotional state for logging/debugging.
        """
        return {
            "current_mood": self.current_mood,
            "turn_count": self.turn_count,
            "silence_count": self.silence_count,
            "mood_history": self.mood_history[-10:],  # Last 10
        }
