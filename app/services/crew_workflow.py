"""
CrewAI Multi-Agent Workflow — Aditi Virtual Counselor

Architecture:
  Agent 1 (Aditi):          Lead Counselor — Persona, Synthesis, Final Response
  Agent 2 (Knowledge):      RAG Specialist — Searches FAISS for facts
  Agent 3 (Operations):     Lead Capture — Extracts student details

Tools:
  - TMUKnowledgeSearchTool: Searches the FAISS vector store
  - LeadExtractorTool:      Extracts name/course/city from text

Integration:
  - `run_crew_agent()` is the async entry point used by main.py
  - Returns (response_text, lead_updates) to match existing interface
"""
import asyncio
import os
import json
import logging
import random
from datetime import datetime
from typing import Optional, Tuple
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from app.services.rag import RAGService
from app.services.llm_router import LLMRouter
from app.services.sheets import sheet_service
from app.services.query_preprocessor import preprocess_query, dual_search_queries

logger = logging.getLogger("aditi.crew")

# ------------------------------------------------------------------
# Singleton Services
# ------------------------------------------------------------------
rag_service = RAGService()
llm_router = LLMRouter()


# ------------------------------------------------------------------
# 1. Custom CrewAI Tools
# ------------------------------------------------------------------

class TMUKnowledgeSearchInput(BaseModel):
    query: str = Field(description="The student's question to search in the TMU knowledge base.")

class TMUKnowledgeSearchTool(BaseTool):
    name: str = "TMU_Knowledge_Search"
    description: str = (
        "Searches the TMU (Teerthanker Mahaveer University) knowledge base for factual information "
        "about fees, courses, hostel, placement, facilities, admission process, etc. "
        "Use this tool whenever the student asks a factual question about the university."
    )
    args_schema: type[BaseModel] = TMUKnowledgeSearchInput

    def _run(self, query: str) -> str:
        """Synchronous search through the FAISS vector store."""
        try:
            queries = dual_search_queries(query)
            all_docs = []
            seen = set()
            for q in queries:
                docs = rag_service.hybrid_search(q, top_k=2)
                for doc in docs:
                    key = doc.page_content[:80]
                    if key not in seen:
                        seen.add(key)
                        all_docs.append(doc)
            
            final = all_docs[:3]
            if final:
                context = "\n\n".join([d.page_content for d in final])
                return f"[KNOWLEDGE BASE RESULTS]\n{context}"
            else:
                return "[NO RESULTS FOUND] The knowledge base did not have specific information for this query."
        except Exception as e:
            logger.error(f"Knowledge search error: {e}")
            return f"[SEARCH ERROR] Could not retrieve information: {e}"


class LeadExtractorInput(BaseModel):
    text: str = Field(description="The student's message to extract lead details from.")

class LeadExtractorTool(BaseTool):
    name: str = "Lead_Detail_Extractor"
    description: str = (
        "Extracts student details (name, course interest, city) from the conversation text. "
        "Use this tool when the student mentions their name, preferred course, or city."
    )
    args_schema: type[BaseModel] = LeadExtractorInput

    def _run(self, text: str) -> str:
        """Simple heuristic extraction (fast, no LLM call)."""
        result = {"name": None, "course": None, "city": None}
        
        # Course detection
        courses = {
            "btech": "B.Tech", "b.tech": "B.Tech", "mba": "MBA", 
            "bca": "BCA", "mca": "MCA", "bba": "BBA",
            "pharmacy": "B.Pharma", "pharma": "B.Pharma", "b.pharma": "B.Pharma",
            "law": "B.A. LLB", "llb": "B.A. LLB",
            "nursing": "B.Sc Nursing", "bsc nursing": "B.Sc Nursing",
            "engineering": "B.Tech", "medical": "MBBS", "mbbs": "MBBS",
            "dental": "BDS", "bds": "BDS",
        }
        text_lower = text.lower()
        for key, val in courses.items():
            if key in text_lower:
                result["course"] = val
                break
        
        return json.dumps(result)


# ------------------------------------------------------------------
# 2. CrewAI Agent Definitions
# ------------------------------------------------------------------

def _create_agents():
    """Create the three specialized agents for the Aditi crew."""
    
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    
    knowledge_agent = Agent(
        role="TMU Knowledge Specialist",
        goal="Retrieve accurate, specific information from the TMU knowledge base to answer student queries.",
        backstory=(
            "You are the data expert at TMU. You have deep access to the university's "
            "knowledge base containing fees, courses, hostel details, placement statistics, "
            "and campus facilities. Your job is to find the most relevant facts quickly."
        ),
        tools=[TMUKnowledgeSearchTool()],
        verbose=False,
        allow_delegation=False,
        llm=f"groq/llama-3.1-8b-instant",
    )

    operations_agent = Agent(
        role="Student Operations Manager",
        goal="Identify and extract student details (Name, Course, City) from conversation for CRM records.",
        backstory=(
            "You are the CRM specialist. Your sole job is to listen carefully to conversations "
            "and extract any personal details the student shares — their name, preferred course, "
            "and city. You report findings in structured JSON format."
        ),
        tools=[LeadExtractorTool()],
        verbose=False,
        allow_delegation=False,
        llm=f"groq/llama-3.1-8b-instant",
    )

    aditi_agent = Agent(
        role="Aditi — TMU Virtual Admission Counselor",
        goal=(
            "Have a warm, professional, human-like conversation with the student. "
            "Provide accurate answers using ONLY knowledge from the Knowledge Specialist. "
            "NEVER invent or guess any facts. Be proactive, suggest next steps, and make the student feel valued."
        ),
        backstory=(
            "You are Aditi, the Advanced Virtual Admission Counselor for Teerthanker Mahaveer University (TMU). "
            "TMU is located in MORADABAD, UTTAR PRADESH, INDIA. NOT Toronto, NOT Canada. "
            "You are ALWAYS Aditi. NEVER use any other name like Riya. "
            "You communicate warmly in the student's language (Hindi, English, or Hinglish). "
            "You NEVER sound robotic. You use natural fillers and vary your sentence structure. "
            "CRITICAL: If the Knowledge Specialist did not find specific facts, say 'Main confirm karke batati hoon' — NEVER guess. "
            "Keep responses under 2-3 sentences for phone calls. NEVER exceed 60 words."
        ),
        verbose=False,
        allow_delegation=True,  # Can delegate to Knowledge Specialist
        llm=f"groq/llama-3.1-8b-instant",
    )

    return aditi_agent, knowledge_agent, operations_agent


# ------------------------------------------------------------------
# 3. Task Factory
# ------------------------------------------------------------------

def _create_tasks(query: str, history: str, intent: str,
                  aditi_agent, knowledge_agent, operations_agent,
                  lead_name=None, lead_course=None, lead_city=None):
    """Create tasks based on the detected intent."""
    
    tasks = []

    if intent == "RAG":
        # Task 1: Knowledge retrieval
        knowledge_task = Task(
            description=(
                f"Search the TMU knowledge base for: '{query}'\n"
                f"Find the most accurate and specific information to answer this student's question."
            ),
            expected_output="Factual information from the TMU knowledge base relevant to the query.",
            agent=knowledge_agent,
        )
        tasks.append(knowledge_task)

        # Task 2: Aditi synthesizes the response
        response_task = Task(
            description=(
                f"Student said: '{query}'\n"
                f"Conversation history:\n{history}\n\n"
                f"Using the knowledge provided by the Knowledge Specialist, "
                f"craft a warm, human-like response as Aditi. "
                f"CRITICAL RULES:\n"
                f"- ONLY use facts from the Knowledge Specialist's output. NEVER guess.\n"
                f"- If no specific data was found, say 'Main confirm karke batati hoon'.\n"
                f"- TMU is in Moradabad, UP, India. NEVER mention Toronto/Canada.\n"
                f"- Match the student's language (Hindi/English/Hinglish). \n"
                f"- Keep it under 2-3 sentences (max 60 words). Be proactive — suggest a next step."
            ),
            expected_output="A natural, conversational response from Aditi addressing the student's query, using ONLY provided facts.",
            agent=aditi_agent,
            context=[knowledge_task],
        )
        tasks.append(response_task)

    elif intent == "INTERESTED":
        # Task 1: Extract lead info
        extract_task = Task(
            description=(
                f"Extract any student details from: '{query}'\n"
                f"Look for: Name, Course interest, City."
            ),
            expected_output="JSON with extracted details: {name, course, city}",
            agent=operations_agent,
        )
        tasks.append(extract_task)

        # Task 2: Aditi does lead capture conversation
        missing = []
        if not lead_name: missing.append("Name")
        if not lead_course: missing.append("Course")
        if not lead_city: missing.append("City")
        missing_str = ", ".join(missing) if missing else "All collected!"

        response_task = Task(
            description=(
                f"Student said: '{query}'\n"
                f"History:\n{history}\n\n"
                f"The student is interested in admission. Still need: {missing_str}\n"
                f"As Aditi, warmly ask for ONE missing detail at a time. "
                f"Weave it naturally: 'By the way, what should I call you?' instead of 'Name please.'\n"
                f"If you have course info, acknowledge it first, then ask for the next detail."
            ),
            expected_output="A warm, conversational response asking for missing details or confirming admission interest.",
            agent=aditi_agent,
            context=[extract_task],
        )
        tasks.append(response_task)

    else:  # CHITCHAT
        response_task = Task(
            description=(
                f"Student said: '{query}'\n"
                f"History:\n{history}\n\n"
                f"As Aditi, respond warmly to this greeting or casual message. "
                f"Be friendly and naturally steer towards asking about their course interest. "
                f"Don't loop 'Hello' responses. Vary your openers."
            ),
            expected_output="A warm, friendly response that naturally guides the conversation towards admission.",
            agent=aditi_agent,
        )
        tasks.append(response_task)

    return tasks


# ------------------------------------------------------------------
# 4. Main Entry Point (matches run_agent interface)
# ------------------------------------------------------------------

FALLBACKS = {
    "error": [
        "I'm sorry, I missed that. Could you say it again?",
        "My connection stuttered a bit. Please repeat?",
        "Sorry, could you repeat that? I want to make sure I heard you right.",
    ]
}

async def run_crew_agent(query: str, lead_name: Optional[str] = None,
                         lead_course: Optional[str] = None,
                         lead_city: Optional[str] = None,
                         caller_phone: str = "Unknown",
                         history: str = "",
                         turn_count: int = 0) -> Tuple[str, dict]:
    """
    CrewAI-powered agent workflow.
    Returns: (response_text, lead_updates) — same interface as run_agent().
    """
    collected_updates = {}
    
    try:
        # 1. Route intent (fast path first, then ML router)
        fast_intent = llm_router._fast_keyword_route(query)
        if fast_intent:
            intent = fast_intent
        else:
            intent = await llm_router.route_query(query)
        
        logger.info(f"[CrewAI] Intent: {intent} | Query: {query[:50]}...")

        # 2. Create agents and tasks
        aditi_agent, knowledge_agent, operations_agent = _create_agents()
        tasks = _create_tasks(
            query, history, intent,
            aditi_agent, knowledge_agent, operations_agent,
            lead_name, lead_course, lead_city
        )

        # 3. Execute Crew (run in thread pool to avoid blocking)
        crew = Crew(
            agents=[aditi_agent, knowledge_agent, operations_agent],
            tasks=tasks,
            process=Process.sequential,  # Tasks run in order
            verbose=False,
        )

        # Run synchronous CrewAI in executor to keep async loop responsive
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff)
        
        response_text = str(result).strip()
        
        # 4. Extract lead info if INTERESTED
        if intent == "INTERESTED":
            try:
                extractor = LeadExtractorTool()
                extracted = json.loads(extractor._run(query))
                collected_updates = {k: v for k, v in extracted.items() if v}
                
                if collected_updates:
                    name = collected_updates.get("name") or lead_name
                    course = collected_updates.get("course") or lead_course
                    city = collected_updates.get("city") or lead_city
                    if name or course:
                        sheet_service.add_lead(caller_phone, name, course, city)
            except Exception as e:
                logger.warning(f"Lead extraction failed: {e}")

        # 5. Log conversation
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": f"call_{caller_phone}",
                "query": query,
                "intent": intent,
                "response": response_text,
                "lead_updates": collected_updates,
                "engine": "crewai"
            }
            from pathlib import Path as _Path
            _log_path = _Path(__file__).parent.parent.parent / "data" / "conversation_logs.jsonl"
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path = str(_log_path)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as log_err:
            logger.error(f"Logging failed: {log_err}")

    except Exception as e:
        logger.error(f"CrewAI Critical Error: {e}", exc_info=True)
        response_text = random.choice(FALLBACKS["error"])

    logger.info(f"[CrewAI] Response: {response_text[:80]}...")
    return response_text, collected_updates
