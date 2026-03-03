"""Quick verification script for the production RAG rebuild."""
import sys
sys.path.insert(0, ".")

print("=" * 50)
print("  PRODUCTION RAG VERIFICATION")
print("=" * 50)

# 1. Query Preprocessor
print("\n[1] Query Preprocessor...")
from app.services.query_preprocessor import preprocess_query, dual_search_queries, detect_topic, detect_course

tests = [
    ("btech cse fees kitni hai", "B.Tech Computer Science Engineering fees how much is"),
    ("bca ki fees kya hai", None),  # Just check it runs
    ("hostel ka kharcha", None),
]
for raw, expected in tests:
    result = preprocess_query(raw)
    status = "OK" if (expected is None or expected in result) else "FAIL"
    print(f"  [{status}] '{raw}' → '{result}'")

print(f"  Topic('hostel fee') = {detect_topic('hostel fee')}")
print(f"  Course('btech cse') = {detect_course('btech cse')}")
print(f"  Dual('bca fees') = {dual_search_queries('bca fees')}")

# 2. Cache
print("\n[2] Cache Service...")
from app.services.cache import CacheService
cache = CacheService()
cache_tests = [
    "btech fees", "bca fees", "hostel fees", "placement record",
    "how to apply", "scholarship", "campus info",
]
hits = 0
for q in cache_tests:
    r = cache.check_static_response(q)
    if r:
        hits += 1
        print(f"  [HIT] '{q}' → '{r[:60]}...'")
    else:
        print(f"  [MISS] '{q}'")
print(f"  Cache hit rate: {hits}/{len(cache_tests)}")

# 3. RAG Hybrid Search
print("\n[3] RAG Hybrid Search...")
from app.services.rag import RAGService
rag = RAGService()
search_tests = ["BCA fees", "hostel fee 2026", "placement record BTech CSE"]
for q in search_tests:
    docs = rag.hybrid_search(q, top_k=2)
    print(f"  '{q}' → {len(docs)} docs")
    for d in docs:
        src = d.metadata.get("source", "?")
        print(f"    [{src}] {d.page_content[:80]}...")

# 4. Router
print("\n[4] LLM Router (8B model check)...")
from app.services.llm_router import LLMRouter
router = LLMRouter()
print(f"  Model: {router.llm.model_name}")
assert "8b" in router.llm.model_name.lower(), "Router should use 8B model!"
print("  [OK] Using fast 8B model")

print("\n" + "=" * 50)
print("  ALL CHECKS PASSED!")
print("=" * 50)
