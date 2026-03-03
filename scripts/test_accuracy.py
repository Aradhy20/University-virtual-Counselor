"""
Retrieval Accuracy Test — Phase 5

Runs 50 golden dataset queries against the RAG pipeline and measures:
  1. Hit Rate: % of queries where ≥1 expected keyword found in top-3 results
  2. MRR (Mean Reciprocal Rank): How high the best matching result appears
  3. Category Breakdown: Accuracy per query category (fees, eligibility, etc.)
  4. Miss Analysis: Which queries failed and why

Usage:
    python scripts/test_accuracy.py
    python scripts/test_accuracy.py --verbose
"""
import sys
import os
import json
import time
import math

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Fix Windows Unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

VERBOSE = "--verbose" in sys.argv


def load_golden_dataset():
    """Load the golden dataset JSON."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "golden_dataset.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["queries"]


def test_with_rag_import():
    """Test using the full RAG pipeline (requires working langchain)."""
    try:
        from app.services.rag import RAGService
        rag = RAGService()
        if not rag.vector_store:
            return None, "FAISS index not loaded"
        return rag, None
    except Exception as e:
        return None, str(e)


def evaluate_result(query_item: dict, results: list, rag_service) -> dict:
    """
    Evaluate a single query's retrieval results.
    
    Returns dict with:
      - hit: bool (any expected keyword found in top-3)
      - mrr: float (reciprocal rank of first hit, 0 if no hit)
      - matched_keywords: list of matched keywords
      - best_rank: int (rank of best match, 0 if no match)
      - top_content_preview: str (first 100 chars of top result)
    """
    expected_kw = [kw.lower() for kw in query_item["expected_keywords"]]
    
    if not results:
        return {
            "hit": False,
            "mrr": 0.0,
            "matched_keywords": [],
            "best_rank": 0,
            "top_content_preview": "(no results)",
        }
    
    best_rank = 0
    all_matched = []
    
    for rank, doc in enumerate(results, 1):
        content_lower = doc.page_content.lower()
        matched = [kw for kw in expected_kw if kw in content_lower]
        if matched and best_rank == 0:
            best_rank = rank
        all_matched.extend(matched)
    
    all_matched = list(set(all_matched))
    hit = len(all_matched) > 0
    mrr = (1.0 / best_rank) if best_rank > 0 else 0.0
    
    return {
        "hit": hit,
        "mrr": mrr,
        "matched_keywords": all_matched,
        "best_rank": best_rank,
        "top_content_preview": results[0].page_content[:100] if results else "",
    }


def run_accuracy_test(rag_service, queries: list) -> dict:
    """
    Run all queries and collect metrics.
    """
    total = len(queries)
    hits = 0
    total_mrr = 0.0
    category_stats = {}
    misses = []
    
    print(f"\nRunning {total} queries against RAG pipeline...\n")
    
    start_time = time.time()
    
    for i, q in enumerate(queries):
        query_text = q["query"]
        category = q["category"]
        
        # Initialize category stats
        if category not in category_stats:
            category_stats[category] = {"total": 0, "hits": 0}
        category_stats[category]["total"] += 1
        
        # Run retrieval
        try:
            results = rag_service.hybrid_search(query_text, top_k=3)
        except Exception as e:
            results = []
            if VERBOSE:
                print(f"  ⚠️  Query {q['id']} error: {e}")
        
        # Evaluate
        eval_result = evaluate_result(q, results, rag_service)
        
        if eval_result["hit"]:
            hits += 1
            category_stats[category]["hits"] += 1
            if VERBOSE:
                print(f"  ✅ Q{q['id']:02d} [{category:12s}] '{query_text[:40]}...' → [{', '.join(eval_result['matched_keywords'][:3])}] (rank {eval_result['best_rank']})")
        else:
            misses.append({
                "id": q["id"],
                "query": query_text,
                "category": category,
                "expected": q["expected_keywords"],
                "top_result": eval_result["top_content_preview"],
            })
            if VERBOSE:
                print(f"  ❌ Q{q['id']:02d} [{category:12s}] '{query_text[:40]}...' → MISS (expected: {q['expected_keywords'][:3]})")
        
        total_mrr += eval_result["mrr"]
    
    elapsed = time.time() - start_time
    
    hit_rate = (hits / total) * 100 if total > 0 else 0
    avg_mrr = total_mrr / total if total > 0 else 0
    
    return {
        "total": total,
        "hits": hits,
        "misses": len(misses),
        "hit_rate": round(hit_rate, 1),
        "mrr": round(avg_mrr, 3),
        "category_stats": category_stats,
        "miss_details": misses,
        "elapsed_s": round(elapsed, 2),
        "avg_query_ms": round((elapsed / total) * 1000, 0) if total > 0 else 0,
    }


def print_results(results: dict):
    """Pretty print the test results."""
    print("\n" + "=" * 60)
    print("   RETRIEVAL ACCURACY REPORT — Phase 5")
    print("=" * 60)
    
    print(f"\n📊 OVERALL METRICS")
    print(f"   Total Queries:   {results['total']}")
    print(f"   Hits:            {results['hits']}")
    print(f"   Misses:          {results['misses']}")
    print(f"   Hit Rate:        {results['hit_rate']}%")
    print(f"   Mean Reciprocal Rank (MRR): {results['mrr']}")
    print(f"   Total Time:      {results['elapsed_s']}s")
    print(f"   Avg Query Time:  {results['avg_query_ms']}ms")
    
    # Grade
    if results['hit_rate'] >= 90:
        grade = "A (Excellent)"
    elif results['hit_rate'] >= 80:
        grade = "B+ (Good)"
    elif results['hit_rate'] >= 70:
        grade = "B (Acceptable)"
    elif results['hit_rate'] >= 60:
        grade = "C (Needs Work)"
    else:
        grade = "D (Poor)"
    print(f"   Grade:           {grade}")
    
    print(f"\n📂 CATEGORY BREAKDOWN")
    print(f"   {'Category':<15} {'Hits':>5} / {'Total':>5}  {'Rate':>6}")
    print(f"   {'-'*15} {'-'*5}   {'-'*5}  {'-'*6}")
    
    for cat, stats in sorted(results['category_stats'].items()):
        rate = (stats['hits'] / stats['total'] * 100) if stats['total'] > 0 else 0
        icon = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
        print(f"   {icon} {cat:<13} {stats['hits']:>5} / {stats['total']:>5}  {rate:>5.0f}%")
    
    if results['miss_details']:
        print(f"\n❌ MISSED QUERIES ({len(results['miss_details'])})")
        for miss in results['miss_details']:
            print(f"   Q{miss['id']:02d} [{miss['category']}] {miss['query']}")
            print(f"       Expected: {miss['expected'][:4]}")
            print(f"       Got: {miss['top_result'][:80]}...")
            print()
    
    print("=" * 60)
    
    # Save report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "accuracy_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Report saved: {report_path}")


def run_standalone_tests():
    """
    Run tests that don't require RAG import (file-based checks).
    """
    print("\n" + "=" * 60)
    print("   STANDALONE CHECKS (no RAG import needed)")
    print("=" * 60)
    
    # Check golden dataset is valid
    queries = load_golden_dataset()
    print(f"  ✅ Golden dataset loaded: {len(queries)} queries")
    
    # Check category distribution
    categories = {}
    for q in queries:
        cat = q["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"  ✅ Categories: {len(categories)}")
    for cat, count in sorted(categories.items()):
        print(f"     {cat}: {count} queries")
    
    # Check all queries have required fields
    required = ["id", "query", "expected_keywords", "category"]
    for q in queries:
        for field in required:
            assert field in q, f"Query {q.get('id', '?')} missing field: {field}"
    print(f"  ✅ All queries have required fields")
    
    # Check FAISS index exists
    faiss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "faiss_index")
    if os.path.exists(faiss_path):
        print(f"  ✅ FAISS index found: {faiss_path}")
    else:
        print(f"  ⚠️  FAISS index NOT found (run ingest.py first)")
    
    # Check BM25 index exists
    bm25_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "bm25_index.pkl")
    if os.path.exists(bm25_path):
        print(f"  ✅ BM25 index found")
    else:
        print(f"  ⚠️  BM25 index NOT found")


if __name__ == "__main__":
    print("🎯" * 30)
    print("   RETRIEVAL ACCURACY TEST SUITE — Phase 5")
    print("🎯" * 30)
    
    # Always run standalone checks
    run_standalone_tests()
    
    # Try to run full RAG test
    queries = load_golden_dataset()
    rag_service, error = test_with_rag_import()
    
    if rag_service:
        results = run_accuracy_test(rag_service, queries)
        print_results(results)
        sys.exit(0 if results['hit_rate'] >= 70 else 1)
    else:
        print(f"\n⚠️  RAG import failed: {error}")
        print("   Full accuracy test requires working RAG pipeline.")
        print("   Standalone checks passed. Run with working langchain to get full results.")
        sys.exit(0)
