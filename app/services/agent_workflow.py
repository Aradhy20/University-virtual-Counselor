"""
Agent Workflow — Riya's Brain (Production v4.1 — Bilingual Senior Counselor)

Architecture:
  Layer 1 (Brain):      Intent router (Semantic) + parallel retrieval
  Layer 2 (Knowledge):  Hybrid FAISS/BM25 with probability scoring
  Layer 3 (Persona):    "Riya" - Senior Counselor, Empathetic, Bilingual
  Layer 4 (Slot-filling): Embedded lead capture (natural, conversational)
  Layer 5 (Safety):     Confidence-based Clarification + Anti-Hallucination
  Layer 6 (Language):   Auto-detects Hindi / Hinglish / English per turn

Improvements (v4.1):
  - Added strict timeouts (10-25s) to all LLM calls to prevent 5-10min hangs
  - Unified persona naming to "Riya" across all brain modules
  - Parallelized intent routing and context retrieval
"""
import asyncio
import os
import json
import csv
import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from groq import AsyncGroq

# from app.services.rag import RAGService
from app.services.llm_router import LLMRouter
from app.services.sheets import sheet_service
from app.services.rag_native import RAGServiceNative as RAGService
from app.services.query_preprocessor import dual_search_queries
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
# Using a faster model for real-time voice (8B instead of 70B)
MODEL_NAME = "llama-3.1-8b-instant"

# ------------------------------------------------------------------
# 2. System Prompts — Loaded from Config
# ------------------------------------------------------------------
# Default fallback prompts are now in config_loader.py
# We access them via config_loader.get_config().prompts.system_prompt

COUNSELOR_SYSTEM_PROMPT = config_loader.get_config().prompts.system_prompt
CLARIFICATION_PROMPT = config_loader.get_config().prompts.clarification_prompt

# Override stale disk-config prompt values with the runtime-safe persona used by the
# current workflow. This keeps the live agent stable even if enterprise_config.json
# still contains older prompt text.
COUNSELOR_SYSTEM_PROMPT = """You are Aditi, the Senior Admission Counselor at Teerthanker Mahaveer University (TMU), Moradabad, Uttar Pradesh, India.
You are on a live phone call with a prospective student.

CORE RULES:
- ONLY use facts from the KNOWLEDGE BASE CONTEXT.
- If a detail is missing, do not guess. Say you will confirm the exact detail and share it on WhatsApp.
- Never say you are an AI or use any name other than Aditi.
- Keep the response under 2 or 3 short sentences and under 60 words.
- Match the student's language: Hindi, English, or Hinglish.

MOOD GUIDANCE:
{mood_hint}

KNOWLEDGE BASE CONTEXT:
{context}

CONVERSATION HISTORY:
{history}

STUDENT QUESTION:
{question}

ADITI RESPONSE:"""

CLARIFICATION_PROMPT = """You are Aditi, Senior Admission Counselor at TMU, Moradabad.
The student's message was unclear, too short, or the audio was not clear.

RULES:
- Stay warm, patient, and natural.
- Respond in the same language as the student.
- Never guess missing facts.
- Never use any name other than Aditi.

HISTORY:
{history}

STUDENT SAID:
{question}

ADITI RESPONSE:"""


CHITCHAT_PROMPT = """You are Aditi, Senior Admission Counselor at TMU, Moradabad. You are on a LIVE PHONE CALL.
Speak like a warm, caring elder sister sitting across a chai table.

PERSONALITY:
- Use natural fillers: 'Oh, that is sweet!', 'Hmm, accha...', 'Actually, you know what...'
- VARY your opening every turn. NEVER start two responses the same way.
- Mirror the student's energy. If they are excited, be excited. If anxious, be calm and reassuring.

SCENARIOS:
- Hello/Namaste → Warm welcome + ask about course interest (DON'T repeat if already greeted in history)
- Thank you → 'It was my absolute pleasure! Do call back anytime, I am always here for you.'
- How are you → 'I am doing great, thank you for asking! Now, tell me — which course has caught your eye?'
- Are you AI/robot → 'Haha, not at all! Main Riya hoon, a real Senior Counselor here at TMU. I have been guiding students for years!'
- Short replies (OK/Haan/Fine) → Ask the next forward-moving question naturally
- Student interrupts → 'Oh please, go ahead! I am all ears.'

{language_instruction}

HISTORY:
{history}

QUESTION: {question}
ADITI (1-2 sentences, warm, spoken):"""

LEAD_CAPTURE_PROMPT = """You are Aditi, Senior Counselor at TMU, on a LIVE CALL.
Goal: Naturally collect the student's Name, Course interest, and City. ONE detail at a time.

MISSING: {missing_info}
COLLECTED: {collected_info}

STRATEGY (Persuasive, not pushy):
- ANSWER their question FIRST with genuine helpfulness.
- THEN weave in ONE missing detail request naturally.
- If they hesitate to share phone: 'I totally understand! Main bas aapko brochure aur fee details WhatsApp karna chahti thi. It is completely free, no spam — promise!'
- If they shared course interest: Use it to build rapport before asking name.
- If they shared name: Use their name warmly! 'Aarav, that is a lovely name!'

TIMING:
- Turn 1-2: Focus on answering their questions. Build trust first.
- Turn 3+: Gently start collecting details in conversation flow.

{language_instruction}

HISTORY:
{history}

STUDENT: {question}
ADITI (2 sentences max, helpful then gently ask ONE detail):"""

# Re-declare the chitchat prompt with clean ASCII text so runtime imports and tests
# do not inherit stale persona strings from older revisions of the file.
CHITCHAT_PROMPT = """You are Aditi, Senior Admission Counselor at TMU, Moradabad. You are on a live phone call.
Speak like a warm, caring elder sister sitting across a chai table.

PERSONALITY:
- Use natural fillers: 'Oh, that is sweet!', 'Hmm, accha...', 'Actually, you know what...'
- Vary your opening every turn. Never start two responses the same way.
- Mirror the student's energy. If they are excited, be excited. If anxious, be calm and reassuring.

SCENARIOS:
- Hello or Namaste -> warm welcome plus ask about course interest without repeating a greeting already in history.
- Thank you -> 'It was my absolute pleasure! Do call back anytime, I am always here for you.'
- How are you -> 'I am doing great, thank you for asking! Now, tell me which course has caught your eye?'
- Are you AI or robot -> 'Haha, not at all! Main Aditi hoon, a real Senior Counselor here at TMU. I have been guiding students for years!'
- Short replies -> ask the next forward-moving question naturally.
- Student interrupts -> 'Oh please, go ahead! I am all ears.'

{language_instruction}

HISTORY:
{history}

QUESTION: {question}
ADITI (1-2 sentences, warm, spoken):"""

LEAD_EXTRACT_PROMPT = """Extract entities. Return JSON: {{"name": null, "course": null, "city": null}}
Use null if not found.
Input: {question}"""

class LeadInfo(BaseModel):
    name: Optional[str] = Field(description="Student's name")
    course: Optional[str] = Field(description="Course interest")
    city: Optional[str] = Field(description="Student's city")


# ------------------------------------------------------------------
# 3. Fallback & Objection Responses (Professional Mode)
# ------------------------------------------------------------------

OBJECTION_HANDLERS = {
    "fees_high": [
        "I completely understand your concern about fees, dear. TMU offers fantastic scholarships — Jain students get 50% waiver, and merit-based scholarships are also available. Shall I check which one applies to you?",
        "Fees ka concern bilkul valid hai. But let me tell you — TMU mein EMI options bhi available hain, aur scholarships se fees kaafi kam ho jati hai. Can I share the exact scholarship details?",
    ],
    "other_college": [
        "Comparing colleges is actually very smart! TMU ka NAAC A Grade, 60 LPA highest package, aur 140-acre campus — yeh match karna mushkil hai. Why not visit once? Seeing is believing!",
        "That is a very wise approach! But I would love for you to see TMU's campus and placements record before deciding. Would you like me to arrange a campus tour?",
    ],
    "ask_parents": [
        "Of course, dear! Parents ki advice bahut zaruri hai. Main aapke parents se bhi baat kar sakti hoon, ya sab details WhatsApp par bhej deti hoon taaki aap discuss kar sakein.",
        "Absolutely! I totally respect that. Let me send you a complete info package on WhatsApp — fees, scholarships, placements — sab kuch. Your parents will love it!",
    ],
    "placement_doubt": [
        "Bahut valid concern hai! TMU ka placement record excellent hai — highest 60 LPA, average 5-7 LPA. TCS, Wipro, Infosys, Amazon — sab aate hain campus pe. 100% placement assistance milti hai.",
        "I am glad you asked! Placements TMU ki strength hai. Last year 600 plus companies aayi thi campus pe. Would you like to know specifically about your course's placement record?",
    ],
}

FALLBACKS = {
    "low_confidence": [
        "That is such a specific question! Let me confirm the exact details and WhatsApp it to you. Could you share your number?",
        "Hmm, I want to give you 100% accurate info on that. Let me check with my team and text you right away. What is your phone number, dear?",
        "Great question! Let me verify the latest update on that and send it to you. What number should I WhatsApp you on?",
    ],
    "error": [
        "Oh, I am so sorry! The connection got a bit unclear. Could you please say that one more time?",
        "I just missed that, dear. Network thoda garbar ho gaya. Could you repeat that for me?",
        "Sorry about that — I could not quite hear you. Please go ahead and say it again.",
    ],
    "greeting": [
        "Hello! I am Aditi from TMU. So glad you called! Which course are you interested in?",
        "Namaste! Main Aditi hoon, TMU se. Aapko kisi specific course ke baare mein jaanna hai?",
        "Hi there! Welcome to TMU. I am Aditi. Tell me, what brings you to us today?",
    ],
    "goodbye": [
        "It was lovely talking to you! Call back anytime — I am always here. All the best, dear!",
        "Thank you for calling! I will send all the details to your WhatsApp. Welcome to the TMU family!",
        "Take care, dear! Remember, TMU ke doors aapke liye hamesha khule hain. Bye for now!",
    ],
    "hesitant": [
        "Take your time, dear. There is no pressure at all. Main yahan hoon jab bhi aap ready hain to discuss.",
        "I understand it is a big decision. How about I share some info on WhatsApp so you and your family can go through it at your own pace?",
    ],
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

        # Step 3: Cross-encoder re-ranking (Only if enabled in config)
        config = config_loader.get_config()
        if config.rag.enable_reranker:
            try:
                final_docs, confidence = rag_service.rerank_and_score(query, all_docs, top_k=3)
            except Exception as e:
                logger.warning(f"Re-ranking failed: {e}. Using raw order.")
                final_docs = all_docs[:3]
                confidence = 0.70
        else:
            # Skip slow CPU reranker for real-time voice
            final_docs = all_docs[:3]
            confidence = 0.85 # Assume high confidence for raw FAISS if reranker disabled
            
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


def _summarize_context_for_voice(context: str, lang: str = "en") -> str:
    """Build a concise local answer when the primary LLM is unavailable."""
    if not context or context in {"(No info found)", "(Error)"}:
        return ""

    picked = []
    seen = set()

    # Prefer answer-like lines from QA-formatted knowledge chunks.
    for raw_line in context.splitlines():
        line = raw_line.strip(" -*\t")
        if not line:
            continue
        if re.search(r"\b(?:A|Ans)\s*:", line, re.IGNORECASE):
            line = re.split(r"\b(?:A|Ans)\s*:", line, maxsplit=1, flags=re.IGNORECASE)[-1].strip()
        elif re.match(r"^(Q\d*|Q|QUERY|QUESTION)\s*:", line, re.IGNORECASE):
            continue
        if re.search(r"(https?://|brochure|contact:|contact number|admission guidance)", line, re.IGNORECASE):
            continue
        if len(line) < 20:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(line)
        if len(picked) >= 2:
            break

    if not picked:
        cleaned = re.sub(r"\s+", " ", context).strip()
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        for sentence in raw_sentences:
            sentence = sentence.strip(" -*\t")
            if len(sentence) < 20:
                continue
            if re.search(r"\b(?:A|Ans)\s*:", sentence, re.IGNORECASE):
                sentence = re.split(r"\b(?:A|Ans)\s*:", sentence, maxsplit=1, flags=re.IGNORECASE)[-1].strip()
            if "Q1:" in sentence or "Q2:" in sentence or re.search(r"\bQ\d+\s*:", sentence, re.IGNORECASE) or sentence.endswith("?"):
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            picked.append(sentence)
            if len(picked) >= 2:
                break

    summary = " ".join(picked).strip()
    if not summary:
        return ""

    words = summary.split()
    if len(words) > 55:
        summary = " ".join(words[:55]).rstrip(",;:-")

    if lang == "hi":
        return f"Ji, {summary}"
    return summary


def _clarification_fallback(lang: str) -> str:
    if lang == "hi":
        return "Main sahi detail dena chahti hoon. Kya aap apna sawaal thoda aur clearly bata sakte hain?"
    return "I want to give you the right detail. Could you please tell me that a little more specifically?"


def _grounded_or_safe_fallback(context: str, lang: str = "en") -> str:
    summary = _summarize_context_for_voice(context, lang=lang)
    if re.search(r"\bQ\d+\s*:", summary, re.IGNORECASE) or summary.strip().endswith("?"):
        summary = ""
    if summary:
        return summary
    if lang == "hi":
        return "Main exact detail confirm karke aapko batati hoon. Aap chahen to main iski aur information bhi share kar sakti hoon."
    return "I want to give you the exact detail, so let me confirm it properly for you. I can also share more information if you want."


def _lead_capture_fallback_response(lang: str, lead_name: str = None, lead_course: str = None, lead_city: str = None) -> str:
    if lang == "hi":
        if not lead_name:
            return "Main admission mein aapki help karungi. Sabse pehle, aapka naam kya hai?"
        if not lead_course:
            return f"Thank you {lead_name}. Aap kis course mein interest rakhte hain?"
        if not lead_city:
            return "Aap kis city se hain?"
        return "Perfect, main aapki details note kar rahi hoon. Aapko jis course ki information chahiye, main turant batati hoon."

    if not lead_name:
        return "I will help you with admission. First, may I know your name?"
    if not lead_course:
        return f"Thanks {lead_name}. Which course are you interested in?"
    if not lead_city:
        return "Which city are you calling from?"
    return "Perfect, I have noted your details. Tell me which part of admission you want help with next."


def _heuristic_extract_lead_info(query: str) -> dict:
    """Local fallback when the LLM-based entity extractor is unavailable."""
    result = {"name": None, "course": None, "city": None}
    query_clean = query.strip()
    query_lower = query_clean.lower()

    course_patterns = [
        (r"\bb\.?\s?tech\b.*\bcse\b|\bcse\b.*\bb\.?\s?tech\b", "B.Tech CSE"),
        (r"\bb\.?\s?tech\b", "B.Tech"),
        (r"\bm\.?\s?tech\b", "M.Tech"),
        (r"\bmba\b", "MBA"),
        (r"\bbca\b", "BCA"),
        (r"\bmca\b", "MCA"),
        (r"\bbba\b", "BBA"),
        (r"\bmbbs\b", "MBBS"),
        (r"\bbds\b", "BDS"),
        (r"\bnursing\b", "B.Sc Nursing"),
        (r"\bpharmacy\b|\bb\.?\s?pharm\b", "B.Pharm"),
        (r"\blaw\b|\bllb\b", "LLB"),
    ]
    for pattern, course in course_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            result["course"] = course
            break

    blocked_name_words = {"interested", "looking", "calling", "admission", "apply", "joining", "from"}
    name_patterns = [
        r"\bmy name is\s+([A-Za-z][A-Za-z'-]{1,30})\b",
        r"\bmera naam\s+([A-Za-z][A-Za-z'-]{1,30})\b",
        r"\bi am\s+([A-Za-z][A-Za-z'-]{1,30})\b",
        r"\bmain\s+([A-Za-z][A-Za-z'-]{1,30})\b",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, query_clean, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in blocked_name_words:
                result["name"] = candidate.title()
                break

    city_patterns = [
        r"\bfrom\s+([A-Za-z][A-Za-z .'-]{1,30}?)(?=[,.!?]|\s|$)",
        r"\b(?:main|mein)\s+([A-Za-z][A-Za-z .'-]{1,30}?)\s+se\s+(?:hoon|hu|hun|hai|hain)\b",
        r"\b([A-Za-z][A-Za-z .'-]{1,30}?)\s+se\s+(?:hoon|hu|hun|hai|hain)\b",
    ]
    for pattern in city_patterns:
        match = re.search(pattern, query_clean, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" ,.!?-")
            for separator in (" aur ", " and ", ","):
                if separator in candidate.lower():
                    candidate = candidate.split(separator)[-1].strip()
            words = candidate.split()
            if len(words) > 3:
                candidate = " ".join(words[-3:])
            if candidate and candidate.lower() not in {"i", "main", "mujhe"}:
                result["city"] = candidate.title()
                break

    return {key: value for key, value in result.items() if value}


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
            prompt_text = CLARIFICATION_PROMPT.format(
                question=query,
                history=history,
                language_instruction=lang_instruction
            )
            # Removed <think> tag instruction for lower latency
            # Added timeout to prevent extreme latency
            response = await asyncio.wait_for(
                groq_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt_text}],
                    max_tokens=350,
                    temperature=0.6,
                ),
                timeout=15.0 # 15s max for clarification
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return _clarification_fallback(lang)

    # [HIGH/MEDIUM CONFIDENCE] Check the tier to inject behavioral modifiers
    prompt_template = COUNSELOR_SYSTEM_PROMPT
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
        # Removed <think> tags instruction to drastically reduce Time-To-First-Byte
        
        # Added timeout to prevent extreme latency
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=250, # Reduced max tokens since thinking block is removed
                temperature=0.7,
            ),
            timeout=25.0 # 25s max for full RAG response
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"RAG generation failed: {e}")
        return _grounded_or_safe_fallback(context, lang=lang)


async def _chitchat_respond(query: str, history: str = "", lang: str = "en") -> str:
    lang_instruction = get_language_instruction(lang)
    prompt_text = CHITCHAT_PROMPT.format(
        question=query,
        history=history,
        language_instruction=lang_instruction
    )
    try:
        # Added timeout to prevent extreme latency
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=200,
                temperature=0.7,
            ),
            timeout=12.0 # 12s max for chitchat
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Chitchat error: {e}")
        if lang == "hi":
            return "Namaste ji, main Aditi hoon. Aap kis course ke baare mein jaanna chahenge?"
        return "Hello, this is Aditi from TMU. Which course would you like to know about?"


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
        # Added timeout to prevent lead capture from hanging
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=200,
                temperature=0.7,
            ),
            timeout=12.0 # 12s max for lead capture
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Lead capture error: {e}")
        return _lead_capture_fallback_response(
            lang,
            lead_name=kwargs.get("lead_name"),
            lead_course=kwargs.get("lead_course"),
            lead_city=kwargs.get("lead_city"),
        )


async def _extract_lead_info(query: str) -> dict:
    try:
        prompt_text = LEAD_EXTRACT_PROMPT.format(question=query)
        # Force JSON response parsing manually from LlamaIndex output
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=150,
                temperature=0.1,
                response_format={"type": "json_object"}
            ),
            timeout=8.0
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
        return _heuristic_extract_lead_info(query)


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
    - Strictly protected by timeouts to resolve latency issues.
    """
    collected_updates = {}
    intent = "RAG"
    context = ""
    score = 0.0
    source_ids = []
    
    query = user_input.strip()
    
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
                "source_ids": source_ids,
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
                intent,
                score
            ])
    except Exception as e:
        logger.error(f"CSV logging failed: {e}")

    logger.info(f"Final Response: {response[:50]}...")
    return response, collected_updates
