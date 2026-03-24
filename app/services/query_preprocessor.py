"""
Query Preprocessor — Hinglish normalization + abbreviation expansion.

Runs BEFORE retrieval to improve FAISS/BM25 match quality.
Supports dual-query strategy: search with both original and normalized query.
"""
import re
import logging

logger = logging.getLogger("aditi.preprocessor")


# ---------------------------------------------------------------
# Course Aliases → Canonical Names
# ---------------------------------------------------------------
COURSE_ALIASES = {
    # Engineering
    "cs": "Computer Science",
    "cse": "Computer Science Engineering",
    "ece": "Electronics and Communication Engineering",
    "ee": "Electrical Engineering",
    "me": "Mechanical Engineering",
    "ce": "Civil Engineering",
    "it": "Information Technology",
    "ai": "Artificial Intelligence",
    "ml": "Machine Learning",
    "ds": "Data Science",
    # Short forms
    "btech": "B.Tech",
    "b tech": "B.Tech",
    "b.tech": "B.Tech",
    "mtech": "M.Tech",
    "m tech": "M.Tech",
    "bca": "BCA",
    "b.c.a": "BCA",
    "mca": "MCA",
    "m.c.a": "MCA",
    "bba": "BBA",
    "b.b.a": "BBA",
    "mba": "MBA",
    "m.b.a": "MBA",
    "mbbs": "MBBS",
    "m.b.b.s": "MBBS",
    "bds": "BDS",
    "b.d.s": "BDS",
    "bpharm": "B.Pharm",
    "b pharm": "B.Pharm",
    "b.pharm": "B.Pharm",
    "mpharm": "M.Pharm",
    "llb": "LLB",
    "l.l.b": "LLB",
    "ba llb": "BA LLB",
    "ballb": "BA LLB",
    "bped": "B.P.Ed",
    "mped": "M.P.Ed",
    "bsc": "B.Sc",
    "msc": "M.Sc",
    "bcom": "B.Com",
    "mcom": "M.Com",
    "bed": "B.Ed",
    "med": "M.Ed",
    "phd": "Ph.D",
    "dpharm": "D.Pharm",
    "d pharm": "D.Pharm",
}

# Short aliases like "me" and "it" are ambiguous in normal speech.
# Only expand them when the surrounding words clearly indicate course context.
AMBIGUOUS_SHORT_ALIASES = {"ai", "ce", "cs", "ds", "ee", "it", "me", "ml"}
COURSE_CONTEXT_WORDS = {
    "admission", "branch", "course", "degree", "diploma", "engineering",
    "program", "programme", "specialization", "stream", "subject",
    "btech", "b.tech", "mtech", "m.tech", "mba", "bca", "mca", "bba",
}

# ---------------------------------------------------------------
# Hinglish → English Normalization
# ---------------------------------------------------------------
HINGLISH_MAP = {
    # Question words
    "kitni": "how much",
    "kitna": "how much",
    "kitne": "how many",
    "kya": "what",
    "kab": "when",
    "kaise": "how",
    "kahan": "where",
    "kaun": "who",
    "kyun": "why",
    "konsa": "which",
    "konsi": "which",
    # Common words
    "hai": "is",
    "hain": "are",
    "ka": "of",
    "ki": "of",
    "ke": "of",
    "mein": "in",
    "se": "from",
    "ko": "to",
    "pe": "on",
    "par": "on",
    "aur": "and",
    "ya": "or",
    "nahi": "not",
    "nahin": "not",
    # University-specific
    "fees": "fees",
    "hostel": "hostel",
    "placement": "placement",
    "campus": "campus",
    "admission": "admission",
    "scholarship": "scholarship",
    "branch": "branch",
    "seat": "seat",
    "cutoff": "cutoff",
    # Verbs
    "chahiye": "want",
    "chahte": "want",
    "batao": "tell",
    "bataiye": "please tell",
    "milega": "will get",
    "milti": "available",
    "dekhna": "see",
    "jaanna": "know",
    "lena": "take",
    # Admission-specific
    "form": "application form",
    "bharti": "admission",
    "dakhila": "admission",
    "padhna": "study",
    "padhne": "study",
    # Additional transliterated Hindi
    "kharcha": "expense",
    "paisa": "money",
    "padhai": "studies",
    "naukri": "job",
    "accha": "good",
    "theek": "okay",
    "zaroor": "definitely",
    "jaroor": "definitely",
    "suniye": "listen",
    "samajh": "understand",
    "vishwavidyalaya": "university",
    "vidyalaya": "college",
    "shiksha": "education",
    "pradarshan": "performance",
    # Hindi Devanagari Script → English
    "फीस": "fees",
    "हॉस्टल": "hostel",
    "कोर्स": "course",
    "प्लेसमेंट": "placement",
    "एडमिशन": "admission",
    "स्कॉलरशिप": "scholarship",
    "कैंपस": "campus",
    "ब्रांच": "branch",
    "कॉलेज": "college",
    "यूनिवर्सिटी": "university",
    "पढ़ाई": "studies",
    "नौकरी": "job",
    "पैकेज": "package",
    "सीट": "seat",
    "परीक्षा": "exam",
    "योग्यता": "eligibility",
    "कटऑफ": "cutoff",
    "छात्रवृत्ति": "scholarship",
    "कितनी": "how much",
    "कितना": "how much",
    "क्या": "what",
    "कब": "when",
    "कहाँ": "where",
    "कैसे": "how",
}

# ---------------------------------------------------------------
# Topic Detection — Infer category from query
# ---------------------------------------------------------------
TOPIC_KEYWORDS = {
    "fees": ["fee", "fees", "kitni", "kitna", "cost", "price", "paisa", "charge", "amount"],
    "placement": ["placement", "placements", "package", "salary", "recruit", "job", "company", "naukri"],
    "hostel": ["hostel", "accommodation", "room", "mess", "food", "living"],
    "admission": ["admission", "apply", "application", "form", "process", "deadline", "last date", "bharti"],
    "eligibility": ["eligibility", "eligible", "qualification", "criteria", "required", "marks", "percentage", "cutoff"],
    "scholarship": ["scholarship", "concession", "discount", "waiver", "fee waiver"],
    "course": ["course", "program", "branch", "specialization", "stream", "degree"],
    "campus": ["campus", "infrastructure", "facility", "lab", "library", "wifi"],
    "exam": ["exam", "entrance", "cuet", "jee", "neet", "test"],
}


def preprocess_query(raw_query: str) -> str:
    """
    Normalize Hinglish + expand abbreviations for better retrieval.
    Returns a cleaned, expanded version of the query.
    """
    raw_words = raw_query.strip().split()
    if not raw_words:
        return ""

    words = [re.sub(r"^[^\w]+|[^\w]+$", "", token.lower()) for token in raw_words]
    normalized = []
    index = 0

    while index < len(words):
        token = words[index]
        raw_token = raw_words[index]

        if not token:
            index += 1
            continue

        # Check multi-word aliases first (e.g., "b tech", "ba llb")
        if index + 1 < len(words):
            next_token = words[index + 1]
            bigram = f"{token} {next_token}".strip()
            if next_token and bigram in COURSE_ALIASES:
                normalized.append(COURSE_ALIASES[bigram])
                index += 2
                continue

        if token in COURSE_ALIASES:
            if token not in AMBIGUOUS_SHORT_ALIASES:
                normalized.append(COURSE_ALIASES[token])
            else:
                window = {
                    w for w in words[max(0, index - 2):min(len(words), index + 3)]
                    if w and w != token
                }
                should_expand = (
                    raw_token.isupper()
                    or "." in raw_token
                    or bool(window & COURSE_CONTEXT_WORDS)
                )
                normalized.append(COURSE_ALIASES[token] if should_expand else token)
        elif token in HINGLISH_MAP:
            normalized.append(HINGLISH_MAP[token])
        else:
            normalized.append(token)

        index += 1

    result = " ".join(normalized)
    if result != raw_query.lower().strip():
        logger.info(f"Preprocessed: '{raw_query}' → '{result}'")
    return result


def detect_topic(query: str) -> str:
    """Detect the topic/category of a query from keywords."""
    q = query.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


def detect_course(query: str) -> str:
    """Detect course name from query."""
    q = query.lower()
    for alias, canonical in COURSE_ALIASES.items():
        if alias in q:
            return canonical
    return ""


def dual_search_queries(raw_query: str) -> list[str]:
    """
    Returns list of queries to search with:
    - Original query
    - Normalized query (if different)
    This doubles retrieval accuracy for Hinglish queries.
    """
    original = raw_query.strip()
    normalized = preprocess_query(raw_query)

    queries = [original]
    if normalized.lower() != original.lower():
        queries.append(normalized)

    return queries
