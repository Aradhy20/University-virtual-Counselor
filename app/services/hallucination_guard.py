"""
Post-Generation Hallucination Guard

Scans AI-generated responses for known hallucination patterns
and blocks/modifies them before they reach the student.

This is the LAST LINE OF DEFENSE against factually incorrect responses.
"""

import re
import logging

logger = logging.getLogger("riya.guard")


# Known hallucination patterns to block
HALLUCINATION_PATTERNS = [
    # Wrong location
    (r"\b(toronto|canada|canadian|ontario|vancouver|montreal)\b", "LOCATION"),
    (r"\b(united states|usa|uk|australia|london|new york)\b", "LOCATION"),
    # Wrong test references
    (r"\b(SAT|ACT|GRE|GMAT|TOEFL|IELTS)\b", "FOREIGN_TEST"),
    # Wrong currency
    (r"\b(USD|CAD|AUD|GBP|dollar|pound|euro)\b", "CURRENCY"),
    # Fabricated rankings (be careful — only block obviously wrong ones)
    (r"\b(top 5 in the world|globally ranked|world ranking)\b", "RANKING"),
    # AI disclosure violations
    (r"\b(I am an? (AI|artificial|bot|language model|chatbot|virtual assistant))\b", "AI_DISCLOSURE"),
    (r"\b(as an? (AI|artificial intelligence|language model))\b", "AI_DISCLOSURE"),
    # Identity leaks from the older Riya persona
    (r"\b(main Riya hoon|I am Riya|Riya here|mera naam Riya)\b", "IDENTITY_LEAK"),
    (r"\b(my name is Riya|this is Riya|Riya speaking)\b", "IDENTITY_LEAK"),
    (r"\b(Riya ji|Riya didi)\b", "IDENTITY_LEAK"),
]

# Safe replacement responses by violation type
SAFE_REPLACEMENTS = {
    "LOCATION": "TMU Moradabad, Uttar Pradesh mein located hai. Ek 140-acre green campus hai. Aur kya jaanna chahenge?",
    "FOREIGN_TEST": "TMU mein admission ke liye aap CUET, JEE, ya university entrance exam se apply kar sakte hain. Details bhejoon WhatsApp par?",
    "CURRENCY": "Main exact fee structure confirm karke aapko batati hoon. Aapka WhatsApp number share karenge?",
    "RANKING": "TMU ko NAAC 'A' Grade mili hai aur yeh UP ka ek leading private university hai. Aur kya jaanna chahenge?",
    "AI_DISCLOSURE": "Main Aditi hoon, TMU ki Admission Counselor. Bataiye, kya madad karoon?",
    "IDENTITY_LEAK": "Main Aditi hoon, TMU ki Admission Counselor. Bataiye, kya information chahiye?",
}


def check_response(response: str) -> tuple[str, bool, list[str]]:
    """
    Check an AI response for hallucination patterns.
    
    Returns:
        (cleaned_response, was_modified, violations_found)
    """
    if not response:
        return response, False, []
    
    violations = []
    
    for pattern, violation_type in HALLUCINATION_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            violations.append(violation_type)
    
    if not violations:
        return response, False, []
    
    # Log the violation
    logger.warning(f"🚨 HALLUCINATION DETECTED: {violations} in response: {response[:100]}...")
    
    # Determine the most severe violation and use its safe replacement
    # Priority: IDENTITY_LEAK > LOCATION > AI_DISCLOSURE > others
    priority = ["IDENTITY_LEAK", "LOCATION", "AI_DISCLOSURE", "FOREIGN_TEST", "CURRENCY", "RANKING"]
    
    for v_type in priority:
        if v_type in violations:
            safe_response = SAFE_REPLACEMENTS[v_type]
            logger.info(f"Replaced with safe response for {v_type}")
            return safe_response, True, violations
    
    # Fallback: use first violation's replacement
    first_violation = violations[0]
    return SAFE_REPLACEMENTS.get(first_violation, response), True, violations


def check_response_length(response: str, max_words: int = 60) -> str:
    """
    Enforce maximum response length for voice calls.
    Truncates at sentence boundary if too long.
    """
    words = response.split()
    if len(words) <= max_words:
        return response
    
    # Find the last sentence boundary within the word limit
    truncated = " ".join(words[:max_words])
    
    # Try to end at a sentence boundary
    for end_marker in [". ", "? ", "! ", "। "]:
        last_pos = truncated.rfind(end_marker)
        if last_pos > len(truncated) // 2:  # Only if we keep at least half
            truncated = truncated[:last_pos + 1]
            break
    
    logger.info(f"Response truncated from {len(words)} to {len(truncated.split())} words")
    return truncated.strip()
