import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from app.services.agent_workflow import run_agent

async def test_agent():
    print("Testing Agent Workflow (direct async)...")
    
    queries = [
        "Hello, is this the university?",
        "What courses do you offer in engineering?",
        "I want to apply for MBA",
    ]
    
    for q in queries:
        print(f"\n--- Query: {q}")
        try:
            response = await asyncio.wait_for(run_agent(q), timeout=10.0)
            print(f"    Response: {response}")
            print("    ✅ OK")
        except asyncio.TimeoutError:
            print("    ⏰ TIMEOUT (>10s)")
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())
