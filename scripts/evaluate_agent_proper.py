
import asyncio
import os
import sys
import json
import logging
from datetime import datetime

from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.agent_workflow import run_crew_agent as run_agent

# Setup logging
logging.basicConfig(level=logging.ERROR) # Only show errors to keep output clean

TEST_QUESTIONS = [
    "Do you have international collaborations?", # Previously triggered name capture
    "What is the ranking of TMU?",             # Added to fast route
    "Is there a library?",                     # Added to fast route
    "Can I get admission through CUET?",       # Ambiguous, should be RAG or INTERESTED
    "Do you have a startup cell?",             # Ambiguous
    "Why should I choose TMU?"                 # General
]

async def evaluate_agent_proper():
    print(f"--- Evaluating 'Aditi' Agent (Real Workflow) with {len(TEST_QUESTIONS)} Questions ---\n")
    
    results = []
    
    print(f"{'Question':<50} | {'Response Preview'}")
    print("-" * 100)
    
    start_time = datetime.now()
    
    for i, q in enumerate(TEST_QUESTIONS):
        try:
            # CALL THE ACTUAL AGENT
            response, _ = await run_agent(q, caller_phone="EvalUser")
            
            # Print preview
            clean_resp = response.replace('\n', ' ')
            print(f"{q:<50} | {clean_resp[:100]}...")
            
            results.append({
                "id": i+1,
                "question": q,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            print(f"[ERROR] Failed on '{q}': {e}")
            results.append({
                "id": i+1,
                "question": q,
                "error": str(e)
            })
            
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n[Done] Processed {len(TEST_QUESTIONS)} queries in {duration:.2f}s (Avg: {duration/len(TEST_QUESTIONS):.2f}s/query)")

    # Save Results
    with open("brain_evaluation_proper.json", "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    print(f"Results saved to 'brain_evaluation_proper.json'.")

if __name__ == "__main__":
    asyncio.run(evaluate_agent_proper())
