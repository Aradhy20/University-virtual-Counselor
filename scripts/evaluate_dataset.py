
import asyncio
import json
import logging
import sys
import time

# Add project root to path
sys.path.append(r"d:\tmu\university_counselor")

from app.services.llm_router import LLMRouter

logging.basicConfig(level=logging.ERROR) # Only errors

async def evaluate_dataset():
    dataset_file = "qa_dataset_synthetic.json"
    print(f"--- Evaluating Semantic Router on {dataset_file} ---")
    
    try:
        with open(dataset_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Dataset not found. Run generate_qa_dataset.py first.")
        return

    router = LLMRouter()
    
    correct = 0
    total = len(data)
    start_time = time.time()
    
    failures = []

    print(f"Processing {total} queries...")
    for i, item in enumerate(data):
        query = item["query"]
        expected = item["intent"]
        
        # Route
        predicted = await router.route_query(query)
        
        if predicted == expected:
            correct += 1
        else:
            failures.append({
                "query": query,
                "expected": expected,
                "predicted": predicted
            })
            
        if (i+1) % 50 == 0:
            print(f"  Processed {i+1}/{total}...")

    end_time = time.time()
    duration = end_time - start_time
    avg_latency = (duration / total) * 1000
    
    accuracy = (correct / total) * 100
    
    print("\n--- Results ---")
    print(f"Total Queries: {total}")
    print(f"Correct:       {correct}")
    print(f"Accuracy:      {accuracy:.2f}%")
    print(f"Avg Latency:   {avg_latency:.2f} ms")
    print(f"Total Time:    {duration:.2f} s")
    
    if failures:
        print("\n--- Top Failures (Sample) ---")
        for fail in failures[:10]:
            print(f"Query: '{fail['query']}'")
            print(f"  Expected: {fail['expected']} | Predicted: {fail['predicted']}")
            print("-" * 40)
            
    # Save results
    results = {
        "metrics": {
            "accuracy": accuracy,
            "avg_latency_ms": avg_latency,
            "total_queries": total
        },
        "failures": failures
    }
    with open("evaluation_results_ml.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nFull results saved to evaluation_results_ml.json")

if __name__ == "__main__":
    asyncio.run(evaluate_dataset())
