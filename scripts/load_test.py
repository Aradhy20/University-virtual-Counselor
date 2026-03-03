"""
Load Test — Phase 5

Simulates concurrent users querying the RAG pipeline.
Measures latency percentiles and throughput under load.

Usage:
    python scripts/load_test.py              # 10 concurrent users, 5 queries each
    python scripts/load_test.py --users 20   # 20 concurrent users
    python scripts/load_test.py --queries 10 # 10 queries per user
"""
import sys
import os
import asyncio
import time
import random
import json
import statistics

# Add project root
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


SAMPLE_QUERIES = [
    "BTech CSE ki fees kitni hai?",
    "MBBS eligibility kya hai?",
    "Hostel mein AC milega?",
    "TMU ka NAAC grade?",
    "Scholarship kitni milegi?",
    "MBA admission process?",
    "Placement rate kya hai?",
    "Campus mein library hai?",
    "Law course available hai?",
    "BSc Nursing details batao",
    "BCA course fees?",
    "Admission open hai?",
    "JEE se admission milega?",
    "TMU kahan hai?",
    "Average package kitna hai?",
]


async def simulate_user(user_id: int, rag_service, num_queries: int) -> list[dict]:
    """Simulate a single user making multiple queries."""
    results = []
    for i in range(num_queries):
        query = random.choice(SAMPLE_QUERIES)
        
        start = time.perf_counter()
        try:
            docs = rag_service.hybrid_search(query, top_k=3)
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append({
                "user_id": user_id,
                "query": query,
                "latency_ms": round(elapsed_ms, 1),
                "results_count": len(docs),
                "success": True,
            })
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            results.append({
                "user_id": user_id,
                "query": query,
                "latency_ms": round(elapsed_ms, 1),
                "results_count": 0,
                "success": False,
                "error": str(e),
            })
        
        # Small random delay between queries
        await asyncio.sleep(random.uniform(0.05, 0.2))
    
    return results


async def run_load_test(num_users: int, queries_per_user: int):
    """Run concurrent user simulation."""
    try:
        from app.services.rag import RAGService
        rag_service = RAGService()
        if not rag_service.vector_store:
            print("❌ FAISS index not loaded. Run ingest.py first.")
            return
    except Exception as e:
        print(f"❌ RAG import failed: {e}")
        print("   Load test requires working RAG pipeline.")
        return

    total_queries = num_users * queries_per_user
    print(f"\n🚀 Starting load test: {num_users} concurrent users × {queries_per_user} queries = {total_queries} total\n")
    
    start = time.perf_counter()
    
    # Launch all users concurrently
    tasks = [
        simulate_user(uid, rag_service, queries_per_user)
        for uid in range(num_users)
    ]
    all_results = await asyncio.gather(*tasks)
    
    total_time = time.perf_counter() - start
    
    # Flatten results
    flat_results = [r for user_results in all_results for r in user_results]
    
    # Calculate metrics
    latencies = [r["latency_ms"] for r in flat_results if r["success"]]
    failures = [r for r in flat_results if not r["success"]]
    
    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        avg = statistics.mean(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
    else:
        p50 = p95 = p99 = avg = max_lat = min_lat = 0
    
    throughput = total_queries / total_time if total_time > 0 else 0
    
    # Print results
    print("=" * 60)
    print("   LOAD TEST RESULTS")
    print("=" * 60)
    print(f"\n   Config: {num_users} users × {queries_per_user} queries")
    print(f"   Total Queries:    {total_queries}")
    print(f"   Successful:       {len(latencies)}")
    print(f"   Failed:           {len(failures)}")
    print(f"   Total Time:       {total_time:.2f}s")
    print(f"   Throughput:       {throughput:.1f} queries/sec")
    
    print(f"\n   📊 LATENCY PERCENTILES")
    print(f"   Min:    {min_lat:.0f}ms")
    print(f"   P50:    {p50:.0f}ms")
    print(f"   P95:    {p95:.0f}ms")
    print(f"   P99:    {p99:.0f}ms")
    print(f"   Max:    {max_lat:.0f}ms")
    print(f"   Avg:    {avg:.0f}ms")
    
    # Grade
    if p95 < 500:
        grade = "A (Excellent)"
    elif p95 < 1000:
        grade = "B (Good)"
    elif p95 < 2000:
        grade = "C (Acceptable)"
    else:
        grade = "D (Too Slow)"
    
    print(f"\n   Grade (P95 < 2000ms): {grade}")
    
    if failures:
        print(f"\n   ⚠️  FAILURES:")
        for f in failures[:5]:
            print(f"     User {f['user_id']}: {f['query'][:40]}... → {f.get('error', 'unknown')}")
    
    print("=" * 60)
    
    # Save report
    report = {
        "config": {"users": num_users, "queries_per_user": queries_per_user},
        "total_queries": total_queries,
        "successful": len(latencies),
        "failed": len(failures),
        "total_time_s": round(total_time, 2),
        "throughput_qps": round(throughput, 1),
        "latency_ms": {
            "min": round(min_lat, 0),
            "p50": round(p50, 0),
            "p95": round(p95, 0),
            "p99": round(p99, 0),
            "max": round(max_lat, 0),
            "avg": round(avg, 0),
        },
        "grade": grade,
    }
    
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "load_test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    # Parse args
    num_users = 10
    queries_per_user = 5
    
    if "--users" in sys.argv:
        idx = sys.argv.index("--users")
        num_users = int(sys.argv[idx + 1])
    if "--queries" in sys.argv:
        idx = sys.argv.index("--queries")
        queries_per_user = int(sys.argv[idx + 1])
    
    print("⚡" * 30)
    print("   LOAD TEST — Phase 5")
    print("⚡" * 30)
    
    asyncio.run(run_load_test(num_users, queries_per_user))
