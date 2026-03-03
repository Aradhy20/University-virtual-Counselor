
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging
# Configure logging
logging.basicConfig(level=logging.INFO)

from app.services.agent_workflow import run_agent

async def test_agent():
    print("\n--- Testing Riya V2.1 Agent ---")
    
    # Test 1: High Confidence (Should answer directly)
    query_1 = "Tell me about the B.Tech Computer Science fees."
    print(f"\nUser: {query_1}")
    response_1, _ = await run_agent(query_1)
    print(f"Riya: {response_1}")
    
    # Test 2: Ambiguous/Low Confidence (Should clarify)
    # Asking something vague usually triggers low confidence
    query_2 = "What are the charges?" 
    print(f"\nUser: {query_2}")
    response_2, _ = await run_agent(query_2)
    print(f"Riya: {response_2}")
    
    # Test 3: Chitchat
    query_3 = "Are you a robot?"
    print(f"\nUser: {query_3}")
    response_3, _ = await run_agent(query_3)
    print(f"Riya: {response_3}")

if __name__ == "__main__":
    asyncio.run(test_agent())
