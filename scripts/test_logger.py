
import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.agent_workflow import run_agent

async def test():
    print("Testing run_agent logging...")
    try:
        response, updates = await run_agent(
            query="What are the B.Tech fees?",
            caller_phone="+919999999999",
            history=""
        )
        print(f"Response: {response[:50]}...")
        
        # Check if log exists
        log_path = r"d:\tmu\university_counselor\data\conversation_logs.jsonl"
        if os.path.exists(log_path):
            print("SUCCESS: Log file created.")
            with open(log_path, "r") as f:
                last_line = f.readlines()[-1]
                print(f"Last Log Entry: {last_line}")
        else:
            print("FAILURE: Log file not found.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test())
