"""
Robust Load Test — Phase 5 (Direct FAISS)

Simulates concurrent users querying the vector store directly.
Measures latency and throughput without full RAG overhead (to avoid import errors).
"""
import sys
import os
import asyncio
import time
import random
import statistics
import json

# Add project root
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Configuration
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "faiss_index")

SAMPLE_QUERIES = [
    "BTech CSE fees", "MBBS eligibility", "Hostel AC", "NAAC grade", "Scholarship",
    "MBA admission", "Placement rate", "Campus library", "Law course", "BSc Nursing",
    "BCA fees", "Admission open", "JEE admission", "TMU location", "Average package"
]

class RobustLoadTester:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None

    def load_resources(self):
        print(f"Loading embedding model: {EMBEDDING_MODEL}...")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        print(f"Loading FAISS index from {FAISS_PATH}...")
        self.vector_store = FAISS.load_local(FAISS_PATH, self.embeddings, allow_dangerous_deserialization=True)
        print("Resources loaded successfully.")

    async def simulate_query(self, user_id, query):
        start = time.perf_counter()
        try:
            # Run vector search in thread pool to avoid blocking async loop
            # (FAISS is CPU bound)
            await asyncio.to_thread(self.vector_store.similarity_search, query, k=3)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {"success": True, "latency_ms": elapsed_ms}
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {"success": False, "latency_ms": elapsed_ms, "error": str(e)}

async def run_load_test(num_users=10, queries_per_user=5):
    tester = RobustLoadTester()
    try:
        tester.load_resources()
    except Exception as e:
        print(f"Failed to load resources: {e}")
        return

    total_queries = num_users * queries_per_user
    print(f"\n🚀 Starting robust load test: {num_users} users × {queries_per_user} queries = {total_queries} total\n")
    
    start_time = time.perf_counter()
    
    tasks = []
    for uid in range(num_users):
        for _ in range(queries_per_user):
            q = random.choice(SAMPLE_QUERIES)
            tasks.append(tester.simulate_query(uid, q))
            # Stagger slightly
            await asyncio.sleep(0.01)
    
    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_time
    
    # Calculate stats
    latencies = [r["latency_ms"] for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    throughput = total_queries / total_time
    
    if latencies:
        avg = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies)*0.95)]
        p99 = sorted(latencies)[int(len(latencies)*0.99)]
    else:
        avg = p50 = p95 = p99 = 0

    print("=" * 60)
    print("   ROBUST LOAD TEST RESULTS (Vector Only)")
    print("=" * 60)
    print(f"   Total Queries:    {total_queries}")
    print(f"   Successful:       {len(latencies)}")
    print(f"   Failed:           {len(failures)}")
    print(f"   Total Time:       {total_time:.2f}s")
    print(f"   Throughput:       {throughput:.1f} qps")
    print(f"\n   📊 Latency (ms)")
    print(f"      Avg: {avg:.1f}")
    print(f"      P50: {p50:.1f}")
    print(f"      P95: {p95:.1f}")
    print(f"      P99: {p99:.1f}")
    print("=" * 60)

    # Save report
    with open("data/robust_load_report.json", "w") as f:
        json.dump({
            "users": num_users,
            "queries": total_queries,
            "throughput": throughput,
            "p95_latency": p95,
            "success_rate": len(latencies)/total_queries*100
        }, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_load_test(20, 5))  # 20 users, 5 queries each = 100 queries
