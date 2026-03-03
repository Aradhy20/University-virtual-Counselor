import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.agent_workflow import app
from langchain_core.messages import HumanMessage

async def main():
    print("--- Testing University Counselor Graph ---")
    
    # Test Query (Hindi)
    query = "Mujhe BTech ki fees janani hai."
    print(f"\n[USER]: {query}")
    
    inputs = {"messages": [HumanMessage(content=query)], "intent": ""}
    
    try:
        final_state = await app.ainvoke(inputs)
        response = final_state["messages"][-1].content
        print(f"\n[AI]: {response}")
        
        print("\n--- Graph Execution Successful ---")
    except Exception as e:
        print(f"\n[ERROR]: Graph execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
