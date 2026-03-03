import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from groq import Groq

# Load Env
load_dotenv(r"d:\tmu\university_counselor\.env")

# 50+ Questions to Test Knowledge Base
TEST_QUESTIONS = [
    "What is the highest package at TMU?",
    "Tell me about the BTech fee structure.",
    "Is there a hostel available for girls?",
    "What are the admission dates for 2026?",
    "Do you offer scholarships?",
    "Is TMU UGC approved?",
    "Where is the campus located?",
    "Can I get admission through CUET?",
    "What is the placement record for MBA?",
    "Do you have a hospital on campus?",
    "What courses do you offer in Medical?",
    "Is there a gym in the hostel?",
    "What is the fee for MBBS?",
    "How do I apply online?",
    "What is the last date to apply?",
    "Is the campus ragging-free?",
    "Do you have a swimming pool?",
    "What is the average package for CSE?",
    "Are there transport facilities?",
    "Is attendance mandatory?",
    "Tell me about the faculty.",
    "Do you have international collaborations?",
    "Is there a library?",
    "What is the dress code?",
    "Can I visit the campus?",
    "Do you have a sports complex?",
    "What is the ranking of TMU?",
    "Is generated AI used in teaching?",
    "Do you offer Ph.D. programs?",
    "What is the eligibility for BBA?",
    "Is there Wi-Fi on campus?",
    "Do you have an incubation center?",
    "What is the fee for BCA?",
    "Do you celebrate cultural fests?",
    "Is there a bank on campus?",
    "What documents are required for admission?",
    "Can I pay fees in installments?",
    "Do you offer education loans?",
    "What is the student-teacher ratio?",
    "Are there research opportunities?",
    "Do you have a mess facility?",
    "Is the food good?",
    "What is the security like?",
    "Do you have a moot court for Law?",
    "What is the fee for Nursing?",
    "Do you offer BDS?",
    "Is there an entrance exam for BTech?",
    "What is the refund policy?",
    "Do you have a startup cell?",
    "Why should I choose TMU?"
]

async def evaluate_brain():
    print(f"--- Evaluating Aditi's Brain (Groq Direct) with {len(TEST_QUESTIONS)} Questions ---")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY missing in .env")
        return

    client = Groq(api_key=api_key)
    results = []
    
    print(f"{'Question':<50} | {'Response Preview'}")
    print("-" * 100)
    
    for q in TEST_QUESTIONS:
        try:
            # Direct Groq Call
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Aditi, a senior admission counselor at TMU. Answer briefly."},
                    {"role": "user", "content": q}
                ],
                temperature=0.1,
                max_tokens=150
            )
            response = completion.choices[0].message.content
            print(f"{q:<50} | {response[:100]}...")
            
            results.append({
                "question": q,
                "response": response
            })
        except Exception as e:
            print(f"[ERROR] Failed on '{q}': {e}")
            results.append({
                "question": q,
                "error": str(e)
            })
            
    # Save Results
    with open("brain_evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\n[SUCCESS] Evaluation Complete. Results saved to 'brain_evaluation_results.json'.")

if __name__ == "__main__":
    asyncio.run(evaluate_brain())
