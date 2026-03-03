import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_router import LLMRouter
from app.services.rag import RAGService
# from app.services.rag_llamaindex import RAGServiceV2 as RAGService
from app.services.agent_workflow import app as agent_app
from app.services.voice import VoiceService

# Load Environment Variables
load_dotenv(r"d:\tmu\university_counselor\.env")

async def test_local_conversation():
    print("--- Aditi Local Voice Test ---")
    print("Initializing Services (LangChain Brain + Deepgram Voice)...")
    
    # 1. Initialize Services
    try:
        rag = RAGService()
        # workflow = AgentWorkflow() # This uses LangGraph
        # voice = VoiceService()
        voice = VoiceService()
        print("[SUCCESS] Services Initialized.")
    except Exception as e:
        print(f"[ERROR] Service Init Failed: {e}")
        return

    # 2. Conversation Loop
    print("\nTalk to Aditi (Type 'exit' to quit):")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        print("Aditi is thinking... (LangChain Processing)")
        
        # 3. Get Response from Brain (LangGraph)
        # We manually invoke the graph or just the RAG for this test.
        # Let's use the workflow's direct invocation if possible, or simulate the router.
        
        # For simplicity in this script, we'll use the RAG service directly as the 'Brain' output
        # But to be true to the architecture, we should route it.
        
        # Simulating the graph flow:
        response_text = ""
        
        # Simple Logic to mimicking the graph for local test
        if "hello" in user_input.lower() or "namaste" in user_input.lower():
            response_text = "Namaste! I am Aditi, an Admission Counselor at TMU. How can I help you today?"
        else:
            # Use RAG (LangChain)
            print("[DEBUG] Calling RAG Service...")
            response_text = await rag.get_answer(user_input)
            print(f"[DEBUG] RAG Response: {response_text}")
            
        print(f"Aditi (Text): {response_text}")
        
        # 4. Generate Audio (ElevenLabs)
        if os.getenv("ELEVENLABS_API_KEY"):
            print("Generating Voice... (ElevenLabs)")
            try:
                # We will just generate and save to a file for verification, not stream to websocket
                # Since voice.service is designed for websockets, we'll use the client directly here for the test file.
                print("[DEBUG] Calling ElevenLabs Generate...")
                audio_stream = voice.eleven.generate(
                    text=response_text,
                    voice="xAmuYLyEOAjjvwszDZPp", # Aditi's Voice
                    model="eleven_turbo_v2",
                    stream=True
                )
                print("[DEBUG] Audio Stream Started. Saving to file...")
                
                output_file = "aditi_response.mp3"
                with open(output_file, "wb") as f:
                    for chunk in audio_stream:
                        if chunk:
                            f.write(chunk)
                            
                print(f"[SUCCESS] Audio saved to {output_file}. Play it to hear Aditi!")
            except Exception as e:
                print(f"[ERROR] Voice Generation Failed: {e}")
        else:
             print("[WARN] ELEVENLABS_API_KEY missing. Skipping voice generation.")

if __name__ == "__main__":
    asyncio.run(test_local_conversation())
