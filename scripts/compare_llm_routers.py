import asyncio
import json
import time
import os
import sys
from groq import AsyncGroq
from dotenv import load_dotenv

# Add project root to path
sys.path.append(r"c:\tmu\university_counselor")

load_dotenv()

MODELS_TO_TEST = [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama3-8b-8192"
]

PROMPT = """You are a router. Classify the user query into ONE of these intents: RAG, INTERESTED, CHITCHAT.
Rules:
- Give ONE word only: RAG, INTERESTED, or CHITCHAT.
- RAG: Information about fees, courses, ranking, hostels. Even if they say "how to admission", if it's info-seeking, it is RAG.
- INTERESTED: They explicitly want to apply, enroll, fill form, or give their name/number.
- CHITCHAT: Greetings, thanks, partings.
"""

async def evaluate_model(client, model_name, dataset_sample):
    correct = 0
    total = len(dataset_sample)
    start_time = time.time()
    
    for i, item in enumerate(dataset_sample):
        query = item["query"]
        expected = item["intent"]
        
        try:
            call_start = time.time()
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                temperature=0.0,
                max_tokens=10
            )
            val = completion.choices[0].message.content.strip().upper()
            
            # Clean response to exact words
            if "RAG" in val: predicted = "RAG"
            elif "INTERESTED" in val: predicted = "INTERESTED"
            elif "CHITCHAT" in val: predicted = "CHITCHAT"
            else: predicted = "UNKNOWN"
            
            if predicted == expected:
                correct += 1
                
        except Exception as e:
            print(f"Error on {model_name}: {e}")
            
    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = (total_time / total) * 1000
    accuracy = (correct / total) * 100
    
    return {
        "model": model_name,
        "accuracy": accuracy,
        "avg_latency_ms": avg_latency
    }

async def main():
    print("--- Starting LLM Router Benchmark ---")
    
    with open(r"c:\tmu\university_counselor\qa_dataset_synthetic.json", "r", encoding="utf-8") as f:
        full_data = json.load(f)
        
    # Test on a random sample of 50 to avoid rate limits and save time
    import random
    random.seed(42)
    sample_data = random.sample(full_data, 50)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Missing GROQ_API_KEY in .env")
        # Fallback to json key from enterprise_config
        with open(r"c:\tmu\university_counselor\data\enterprise_config.json") as f:
            cfg = json.load(f)
            api_key = cfg.get("api", {}).get("groq_api_key")
            
    client = AsyncGroq(api_key=api_key)
    results = []
    
    for model in MODELS_TO_TEST:
        print(f"\nEvaluating {model}...")
        res = await evaluate_model(client, model, sample_data)
        print(f"  Accuracy: {res['accuracy']:.2f}% | Latency: {res['avg_latency_ms']:.2f} ms")
        results.append(res)
        
    print("\n--- Final Results ---")
    results.sort(key=lambda x: (x['accuracy'] / (x['avg_latency_ms']+1)), reverse=True) # Sort by best ratio
    
    for r in results:
        print(f"{r['model']:<25} | {r['accuracy']:>6.2f}% ACC | {r['avg_latency_ms']:>6.2f} ms")
        
    with open("llm_comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\nSaved to llm_comparison_results.json")

if __name__ == "__main__":
    asyncio.run(main())
