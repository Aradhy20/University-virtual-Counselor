"""
Language Detector — Auto-detect Hindi vs English for Aditi's bilingual responses.

Detects language from user input and returns a language code:
  - 'hi'  → Hindi / Hinglish (respond in Hindi + English mix)
  - 'en'  → English (respond in pure English)

Uses keyword frequency to determine language preference.
"""
import re
import logging

logger = logging.getLogger("aditi.language")

# Common Hindi / Hinglish words and Devanagari script detection
HINDI_INDICATORS = [
    # Pure Hindi words (romanized)
    r"\b(mujhe|mera|meri|mere|aapko|aap|hain|hai|kya|kaise|kitni|kitna|batao|bataiye|chahiye|chahte|chahti|kaun|kya|kyun|kyunki|kab|kahan|yahan|udhar|iska|uska|yeh|woh|hum|tum|main|nahi|nahin)\b",
    # Admission-specific Hindi terms
    r"\b(admission|pravesh|pariksha|shulk|fees|hostel|campus|course|program|scholarship|bvishyaa|padhna|padhai|college|university|kitna|accha|theek|bilkul|zarur|jarur|jankari|details)\b",
    # Common Hinglish expressions  
    r"\b(ji|ji haan|haan|nahi|acha|accha|thik|theek|ek dam|ek bar|bata|bata do|bata deen|bataiye|batao|samjhe|samajh|aaya|samjha|pata|pata hai|pata nahi|lagta|lagti|chahta|chahti|lena|lena hai|karna|karo|karna chahta)\b",
    # Time expressions in Hindi
    r"\b(abhi|kal|parso|aaj|baad|pehle|sirf|bas|toh|phir|aur|ya|lekin|magar|isliye|isliye)\b",
]

# Devanagari script pattern (pure Hindi text)
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')

# English-only indicators (confident English speakers)
ENGLISH_STRONG_INDICATORS = [
    r"\b(please|could you|would you|I would like|I want|I need|Could you please|regarding|information about|tell me about|what are the|how do I|is there a|are there any)\b",
]


def detect_language(text: str) -> str:
    """
    Detect whether user is speaking Hindi/Hinglish or English.
    
    Returns:
        'hi' — Hindi/Hinglish detected → respond bilingually
        'en' — English detected → respond in English
    """
    if not text or len(text.strip()) < 2:
        return 'en'
    
    # Check for Devanagari script (pure Hindi text)
    if DEVANAGARI_PATTERN.search(text):
        logger.info("Language: Hindi (Devanagari detected)")
        return 'hi'
    
    text_lower = text.lower().strip()
    
    # Count Hindi indicator hits
    hindi_score = 0
    for pattern in HINDI_INDICATORS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        hindi_score += len(matches)
    
    # Count strong English hits
    english_score = 0
    for pattern in ENGLISH_STRONG_INDICATORS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        english_score += len(matches) * 2  # Weight English higher
    
    # Decision
    if hindi_score >= 2 and hindi_score > english_score:
        logger.info(f"Language: Hindi/Hinglish (score={hindi_score} vs en={english_score})")
        return 'hi'
    elif hindi_score >= 1 and english_score == 0:
        logger.info(f"Language: Hindi/Hinglish (only hindi signals)")
        return 'hi'
    
    logger.info(f"Language: English (en={english_score}, hi={hindi_score})")
    return 'en'


def get_language_instruction(lang: str) -> str:
    """
    Returns a language instruction string to inject into LLM prompt.
    """
    if lang == 'hi':
        return (
            "LANGUAGE: The student is communicating in Hindi/Hinglish. "
            "Respond in a warm mix of simple Hindi and English (Hinglish). "
            "Use English for technical/course names. "
            "Example: 'Aapka B.Tech CSE mein interest hai — excellent choice! "
            "TMU mein fees approximately 1.2 lakh per year hain.' "
            "Keep it natural, warm, and conversational."
        )
    else:
        return (
            "LANGUAGE: The student is communicating in English. "
            "Respond in clear, warm, professional English. "
            "Keep sentences short and conversational."
        )
