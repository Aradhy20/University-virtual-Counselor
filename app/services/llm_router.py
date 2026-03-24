"""
LLM Router — Classifies user intent to route to the correct handler.

Uses Semantic Router (MiniLM embeddings) for fast, accurate classification.
Falls back to RAG for unknown queries.

Categories:
  - RAG: University knowledge queries (fees, courses, admissions, placements)
  - CHITCHAT: Greetings, small talk, thank you, goodbye
  - INTERESTED: EXPLICIT enrollment intent (not info queries about admission)
  - UNKNOWN: Fallback → routes to RAG
"""

import logging
import re
from app.services.semantic_router import SemanticRouter

logger = logging.getLogger("riya.router")


# Keywords that indicate INFO-SEEKING about admission (should be RAG, not INTERESTED)
RAG_OVERRIDE_PATTERNS = [
    r"\b(kya|can|how|what|is|do you|does it|tell|explain|details|batao|bataiye)\b",
    r"\b(cuet|neet|jee|entrance|exam|eligibility|criteria|process|procedure)\b",
    r"\b(fee|fees|structure|cost|kitni|kitna|charges|tuition)\b",
    r"\b(rank|ranking|rating|accredit|naac|nirf|approved)\b",
    r"\b(placement|package|salary|recruit|company|job)\b", 
    r"\b(hostel|campus|facility|library|gym|sports|canteen|mess)\b",
    r"\b(course|programme|program|branch|specialization|stream)\b",
    r"\b(scholarship|discount|waiver|concession)\b",
    r"\b(document|require|submit|upload|form)\b",
    r"\b(why|should|choose|compare|better|best|vs)\b",
    r"\b(startup|incubat|collaborat|international|research)\b",
    r"\b(refund|loan|installment|emi)\b",
    r"\b(btech|b\.tech|mba|bca|mca|bba|pharma|mbbs|bds|nursing|llb|law)\b",
    r"\b(how .{0,20}(apply|join|enroll|register|get admission))\b",
    r"\b(admission .{0,10}(process|procedure|requirement|criteria|date|deadline))\b",
]

# Keywords that indicate GENUINE enrollment intent
INTERESTED_KEYWORDS = [
    r"\b(apply|register|enroll|enrol|admission (lena|chahta|chahti|karao|kara do))\b",
    r"\b(mera naam|my name is|i am \w+, from)\b",
    r"\b(form bhar|form bhej|fill form|apply karna|registration karna)\b",
    r"\b(join karna|join TMU|admission le)\b",
    r"\b(interested hoon|interested in joining)\b",
]

# Chitchat patterns
CHITCHAT_KEYWORDS = [
    r"^(hi|hello|hey|namaste|namaskar|good morning|good afternoon|good evening)[\s!.?]*$",
    r"^(bye|goodbye|alvida|dhanyavad|shukriya|thank you|thanks|ok bye|theek hai)[\s!.?]*$",
    r"^(kaise ho|how are you|kaisi hain)[\s!.?]*$",
    r"^(haan|ok|accha|alright|hmm|ji)[\s!.?]*$",
    r"^(hello|hi|hey)[,\s]+(how are you|how r you)[\s!.?]*$",
    r"^(namaste|namaskar)\s+ji[\s!.?]*$",
]


class LLMRouter:
    def __init__(self):
        # Initialize Semantic Router (Loads MiniLM model)
        self.semantic_router = SemanticRouter()

    def _fast_keyword_route(self, query: str) -> str | None:
        """
        Ultra-fast keyword-based routing for obvious cases.
        Returns intent string or None if uncertain.
        """
        q = query.strip().lower()
        
        # Empty or very short
        if len(q) < 2:
            return "CHITCHAT"
        
        # Check chitchat first (greetings/goodbyes)
        for pattern in CHITCHAT_KEYWORDS:
            if re.match(pattern, q, re.IGNORECASE):
                logger.info(f"Fast route: CHITCHAT (pattern match) for '{q}'")
                return "CHITCHAT"
        
        # Check for info-seeking patterns — these should be RAG even if
        # they mention "admission" (e.g., "How to get admission through CUET?")
        rag_signal_count = 0
        for pattern in RAG_OVERRIDE_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                rag_signal_count += 1
        
        if rag_signal_count >= 2:
            logger.info(f"Fast route: RAG ({rag_signal_count} info signals) for '{q[:40]}'")
            return "RAG"
        
        # Check genuine enrollment intent
        for pattern in INTERESTED_KEYWORDS:
            if re.search(pattern, q, re.IGNORECASE):
                logger.info(f"Fast route: INTERESTED (enrollment match) for '{q[:40]}'")
                return "INTERESTED"
        
        # Uncertain — let semantic router handle it
        return None

    async def route_query(self, query: str) -> str:
        """
        Route query using Semantic Vector Search (Fast & Accurate).
        Falls back to RAG for UNKNOWN intents (safe default for counselor).
        """
        try:
            # 1. Try fast keyword route first
            fast = self._fast_keyword_route(query)
            if fast:
                return fast
            
            # 2. Semantic Routing
            route = await self.semantic_router.route_query(query)
            
            # 3. Override: If semantic says INTERESTED but query looks info-seeking, force RAG
            if route == "INTERESTED":
                q_lower = query.lower()
                info_words = ["kya", "what", "how", "tell", "batao", "details", "fee", 
                             "hostel", "placement", "course", "why", "rank", "facility",
                             "scholarship", "campus", "cuet", "entrance", "eligibility"]
                if any(w in q_lower for w in info_words):
                    logger.info(f"Override: INTERESTED -> RAG (info-seeking detected) for '{query[:40]}'")
                    return "RAG"
            
            # 4. Fallback to RAG if UNKNOWN
            if route == "UNKNOWN":
                logger.info(f"Semantic Router returned UNKNOWN for '{query[:40]}...'. Defaulting to RAG.")
                return "RAG"
                
            return route
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            return "RAG"
