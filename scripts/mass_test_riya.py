import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agent_workflow import run_crew_agent

# A comprehensive list of test cases simulating STT outputs (English, Hindi, Hinglish, errors)
TEST_CASES = [
    # 1. Greetings & Initials
    "Hello",
    "Hi Riya",
    "Namaste",
    "Good morning",
    "Aur kaisi ho",
    
    # 2. General Admission Inquiries
    "I want to take admission.",
    "B.Tech admission process kya hai?",
    "MBBS me seat mil jayegi kya?",
    "BBA ka next batch kab start hoga?",
    "Do you have nursing courses?",
    
    # 3. Fees & Financials
    "MBA ki fees kitni hai?",
    "Hostel fees kya hai per year?",
    "Is there any scholarship for merit students?",
    "Jain minority scholarship milti hai kya?",
    "Can I pay the fees in installments?",
    
    # 4. Campus & Facilities
    "Hostel me khana kaisa hai?",
    "Is the campus safe for girls?",
    "Kya campus me WiFi hai?",
    "Ragging hoti hai kya wahan?",
    "Library facilities kaisi hain?",
    
    # 5. Out of Context / Persona Testing
    "Are you an AI or a robot?",
    "Tumhara asli naam kya hai?",
    "Linux me directory kaise banate hain?",
    "Tell me a joke.",
    "Who is the Prime Minister of India?",
    
    # 6. Unclear / Short / STT errors
    "ok",
    "hmm",
    "haan",
    "hello hello awaz aa rahi hai?",
    "kya bola mujhe samajh nahi aaya",
    "network issue",
    "  ", # basically empty
]

async def run_mass_tests():
    print(f"Starting Mass Test Suite for Riya ({len(TEST_CASES)} base test cases).")
    print("Testing response speed, persona consistency, and hallucination guards...\n")
    
    success_count = 0
    total_time = 0
    
    # We will run them sequentially to avoid hitting Groq API rate limits instantly
    for i, test_input in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] 🙎‍♂️ STUDENT: '{test_input}'")
        start_time = time.time()
        
        try:
            # call the workflow
            response, state_updates = await run_crew_agent(
                user_input=test_input,
                user_name=None,
                user_course=None,
                user_city=None,
                caller_phone="TEST_PHONE",
                history="",
                turn_count=1,
                mood_hint="Neutral"
            )
            elapsed = time.time() - start_time
            total_time += elapsed
            
            print(f"      👩‍💼 RIYA ({elapsed:.2f}s): {response}")
            # Ensure it's not a generic failure
            if len(response) > 5:
                success_count += 1
                
        except Exception as e:
            print(f"      ❌ ERROR: {e}")
            
        print("-" * 60)
        # Small sleep to respect rate limits
        await asyncio.sleep(0.5)
        
    print("\n" + "="*60)
    print(f"🏁 TEST SUITE COMPLETED")
    print(f"Successful Responses: {success_count}/{len(TEST_CASES)}")
    avg_latency = total_time / len(TEST_CASES) if TEST_CASES else 0
    print(f"Average Response Latency: {avg_latency:.2f}s")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_mass_tests())
