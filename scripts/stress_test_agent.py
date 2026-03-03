
import asyncio
import sys
import time
import random
from datetime import datetime

# Add project root to path
sys.path.append(r"d:\tmu\university_counselor")

from app.services.agent_workflow import run_agent

# Test Queries (Mix of RAG, Chitchat, Lead Capture)
QUERIES = [
    "What is the fee for BTech?",
    "Namaste Aditi ji",
    "I want to join TMU",
    "Hostel facilities kaisi hain?",
    "Is placement good for MBA?",
    "Tell me about scholarship",
    "Where is the campus?",
    "My name is Rahul from Delhi",
    "Bye",
    "Course details please"
]

CONCURRENT_REQUESTS = 20  # Simulate 20 concurrent users
TOTAL_REQUESTS = 50       # Total requests to run in this test

async def stress_test():
    print(f"--- Stress Testing Aditi Agent ---")
    print(f"Concurrency: {CONCURRENT_REQUESTS}")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    
    start_time = time.time()
    
    tasks = []
    for i in range(TOTAL_REQUESTS):
        query = random.choice(QUERIES)
        user_id = f"User{i}"
        tasks.append(run_agent(query, caller_phone=user_id))
        
        # Adding slight delay to stagger start times slightly
        if i % CONCURRENT_REQUESTS == 0:
            await asyncio.sleep(0.5)
            
    print(f"launching {len(tasks)} tasks...")
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = 0
    error_count = 0
    errors = []
    
    for res in results:
        if isinstance(res, Exception):
            error_count += 1
            errors.append(str(res))
        else:
            success_count += 1
            
    print(f"\n--- Results ---")
    print(f"Time Taken: {duration:.2f}s")
    print(f"Throughput: {TOTAL_REQUESTS/duration:.2f} req/s")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    
    if errors:
        print("\nTop 5 Errors:")
        for e in errors[:5]:
            print(f"- {e}")
            
    # Save log
    with open("stress_test_log.txt", "w") as f:
        f.write(f"Stress Test at {datetime.now()}\n")
        f.write(f"Success: {success_count}, Errors: {error_count}\n")
        if errors:
            f.write("Errors:\n" + "\n".join(errors))

if __name__ == "__main__":
    asyncio.run(stress_test())
