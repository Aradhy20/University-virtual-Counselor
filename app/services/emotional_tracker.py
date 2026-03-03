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
import logging
from typing import Optional

logger = logging.getLogger("aditi.emotion")


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
        "response_hint": "User is frustrated. Be extra patient, apologize briefly, and give a direct answer.",
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
        "response_hint": "User is anxious. Reassure them, be warm, and provide certainty where possible.",
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
        "response_hint": "User is excited! Match their energy, be enthusiastic, and guide toward action.",
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

    def update(self, user_text: str) -> str:
        """
        Analyze user text and update mood state.
        Returns the current mood.
        """
        self.turn_count += 1
        self.silence_count = 0  # User spoke, reset silence counter

        detected_mood = self._detect_mood(user_text)
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
        Returns None if no nudge needed yet.
        """
        if self.silence_count == 1:
            return "Aap wahan hain? Main sun rahi hoon, bataiye kya help chahiye?"
        elif self.silence_count == 2:
            return "Hello? Agar aap kuch aur jaanna chahte hain toh bataiye, main yahan hoon!"
        elif self.silence_count >= 3:
            return "Lagta hai connection issue hai. Aap dubara call kar sakte hain ya WhatsApp par message kijiye!"
        return None

    def _detect_mood(self, text: str) -> str:
        """
        Detect mood from text using keyword patterns.
        Returns mood category string.
        """
        text_lower = text.lower().strip()
        
        # Skip very short inputs (filler words)
        if len(text_lower) < 3:
            return "neutral"

        # Check each mood category (priority: frustrated > anxious > excited)
        for mood_name in ["frustrated", "anxious", "excited"]:
            patterns = MOODS[mood_name]["keywords"]
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return mood_name

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
