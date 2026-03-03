
import asyncio
import sys
import logging

# Add project root to path
sys.path.append(r"d:\tmu\university_counselor")

from app.services.llm_router import LLMRouter

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_router():
    print("--- Testing Semantic Router ---\n")
    router = LLMRouter()
    
    test_cases = [
        ("What is the fee structure?", "RAG"),
        ("I want to apply for BTech", "INTERESTED"),
        ("Hello Aditi", "CHITCHAT"),
        ("My dad wants to know the cost of MBA", "RAG"), # Semantic match (cost ~ fee)
        ("Can you help me with admission?", "INTERESTED"),
        ("Where is the college?", "RAG"),
        ("Good morning", "CHITCHAT"),
        ("Do you have a gym?", "RAG"),
        ("I am looking for a job", "RAG"), # Might be RAG (placements) or INTERESTED? Let's see.
        ("What is the highest package?", "RAG")
    ]
    
    score = 0
    with open("tests/router_results.txt", "w", encoding="utf-8") as f:
        for i, (query, expected) in enumerate(test_cases):
            try:
                print(f"Testing [{i+1}/{len(test_cases)}]: '{query}'")
                predicted = await router.route_query(query)
                match = "✅" if predicted == expected else "❌"
                result_line = f"Query: '{query}' | Expected: {expected} | Predicted: {predicted} {match}"
                print(result_line)
                f.write(result_line + "\n")
                if predicted == expected:
                    score += 1
            except Exception as e:
                err_msg = f"[ERROR] Failed on '{query}': {e}"
                print(err_msg)
                f.write(err_msg + "\n")
                
        f.write(f"\nAccuracy: {score}/{len(test_cases)} ({score/len(test_cases)*100}%)")

if __name__ == "__main__":
    asyncio.run(test_router())
