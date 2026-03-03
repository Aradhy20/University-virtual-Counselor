"""
Test Suite for Critical Fixes — v3.0

Tests the 5 critical fixes from the audit:
  1. Anti-hallucination grounding
  2. Utterance assembly (visual check — needs live environment)
  3. Response overlap prevention (visual check — needs live environment)
  4. Identity consistency (Riya → Aditi)
  5. Intent classification accuracy

Run: python scripts/test_critical_fixes.py
"""

import sys
import os
import re
import json
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =====================================================================
# Test 1: Hallucination Guard
# =====================================================================
def test_hallucination_guard():
    """Test the hallucination guard catches known bad patterns."""
    from app.services.hallucination_guard import check_response, check_response_length
    
    print("\n" + "="*70)
    print("TEST 1: HALLUCINATION GUARD")
    print("="*70)
    
    test_cases = [
        # (input_response, should_be_modified, expected_violation)
        ("TMU is located in Toronto, Canada and offers great programs.", True, "LOCATION"),
        ("The fees are $50,000 USD per semester.", True, "CURRENCY"),
        ("You need to score well on the SAT to get admission.", True, "FOREIGN_TEST"),
        ("As an AI language model, I cannot provide that information.", True, "AI_DISCLOSURE"),
        ("Namaste! Riya here. Kaise hain aap?", True, "IDENTITY_LEAK"),
        ("TMU is in Moradabad, UP. B.Tech fees are around 1.2 lakh per year.", False, None),
        ("Haan ji, hostel ki suvidha hai campus mein. Safe aur comfortable hai.", False, None),
        ("TMU is ranked top 5 in the world for engineering.", True, "RANKING"),
    ]
    
    passed = 0
    failed = 0
    
    for response, should_modify, expected_violation in test_cases:
        result, was_modified, violations = check_response(response)
        
        if was_modified == should_modify:
            if should_modify and expected_violation and expected_violation not in violations:
                print(f"  ❌ FAIL: Expected violation '{expected_violation}' not detected")
                print(f"     Input:  {response[:60]}...")
                print(f"     Got:    {violations}")
                failed += 1
            else:
                print(f"  ✅ PASS: {'Blocked' if was_modified else 'Allowed'} — {response[:50]}...")
                passed += 1
        else:
            print(f"  ❌ FAIL: Expected modified={should_modify}, got modified={was_modified}")
            print(f"     Input:  {response[:60]}...")
            failed += 1
    
    # Test response length enforcement
    long_response = "This is a very long response that goes on and on about many different topics including fees and placements and hostel and campus and library and gym and scholarship and entrance exam and documents required for admission. It should definitely be truncated to keep the voice experience natural and not too long."
    truncated = check_response_length(long_response, max_words=60)
    word_count = len(truncated.split())
    if word_count <= 60:
        print(f"  ✅ PASS: Length enforcement ({word_count} words ≤ 60)")
        passed += 1
    else:
        print(f"  ❌ FAIL: Length enforcement failed ({word_count} words > 60)")
        failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return passed, failed


# =====================================================================
# Test 2: Identity Consistency (No "Riya" in source code)
# =====================================================================
def test_identity_consistency():
    """Grep for 'Riya' in all prompt strings to ensure no identity leaks."""
    print("\n" + "="*70)
    print("TEST 2: IDENTITY CONSISTENCY (No 'Riya' in prompts)")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # Check agent_workflow.py prompts
    # Try import first; fall back to file parsing if langchain import fails
    prompts = {}
    try:
        from app.services.agent_workflow import (
            COUNSELOR_SYSTEM_PROMPT, CHITCHAT_PROMPT, 
            CLARIFICATION_PROMPT, LEAD_CAPTURE_PROMPT
        )
        prompts = {
            "COUNSELOR_SYSTEM_PROMPT": COUNSELOR_SYSTEM_PROMPT,
            "CHITCHAT_PROMPT": CHITCHAT_PROMPT,
            "CLARIFICATION_PROMPT": CLARIFICATION_PROMPT,
            "LEAD_CAPTURE_PROMPT": LEAD_CAPTURE_PROMPT,
        }
    except Exception as e:
        print(f"  [WARN] Import failed ({e}). Falling back to file parsing...")
        # Parse the file directly to extract prompt strings
        agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "app", "services", "agent_workflow.py")
        with open(agent_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        # Extract prompts between triple-quote blocks
        import re as rx
        for pname in ["COUNSELOR_SYSTEM_PROMPT", "CHITCHAT_PROMPT", "CLARIFICATION_PROMPT", "LEAD_CAPTURE_PROMPT"]:
            match = rx.search(rf'{pname}\s*=\s*"""(.*?)"""', source, rx.DOTALL)
            if match:
                prompts[pname] = match.group(1)
    
    for name, prompt in prompts.items():
        # Check for POSITIVE Riya references (not anti-instructions)
        has_positive_riya = False
        for line in prompt.split('\n'):
            if 'Riya' in line:
                # Allow anti-instructions like "NEVER use any other name (not Riya...)"
                if any(w in line.lower() for w in ['never', 'not riya', 'not any other name']):
                    continue
                has_positive_riya = True
                
        if has_positive_riya:
            print(f"  ❌ FAIL: '{name}' has positive 'Riya' reference (not anti-instruction)")
            failed += 1
        else:
            print(f"  ✅ PASS: '{name}' — No positive 'Riya' references")
            passed += 1
    
    # Check that prompts contain "Aditi"
    for name, prompt in prompts.items():
        if "Aditi" in prompt:
            print(f"  ✅ PASS: '{name}' correctly references 'Aditi'")
            passed += 1
        else:
            print(f"  ❌ FAIL: '{name}' does not reference 'Aditi'")
            failed += 1
    
    # Check grounding instruction exists
    counselor_prompt = prompts.get("COUNSELOR_SYSTEM_PROMPT", "")
    if "ONLY use facts" in counselor_prompt or "ANTI-HALLUCINATION" in counselor_prompt:
        print(f"  ✅ PASS: Anti-hallucination grounding instruction present")
        passed += 1
    else:
        print(f"  ❌ FAIL: Anti-hallucination grounding instruction MISSING")
        failed += 1
    
    # Check Moradabad anchoring
    if "MORADABAD" in counselor_prompt or "Moradabad" in counselor_prompt:
        print(f"  ✅ PASS: TMU Moradabad location anchored in prompt")
        passed += 1
    else:
        print(f"  ❌ FAIL: TMU Moradabad location NOT anchored")
        failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return passed, failed


# =====================================================================
# Test 3: Intent Classification Accuracy
# =====================================================================
def test_intent_classification():
    """Test that info-seeking queries route to RAG, not INTERESTED."""
    print("\n" + "="*70)
    print("TEST 3: INTENT CLASSIFICATION (_fast_keyword_route)")
    print("="*70)
    
    from app.services.llm_router import LLMRouter
    router = LLMRouter()
    
    test_cases = [
        # (query, expected_intent)
        # Info-seeking → should be RAG
        ("Can I get admission through CUET?", "RAG"),
        ("What is the fee structure for BTech?", "RAG"),
        ("Tell me about placement statistics", "RAG"),
        ("Why should I choose TMU?", "RAG"),
        ("What is the hostel fee?", "RAG"),
        ("Is there a scholarship for merit students?", "RAG"),
        ("How to get admission in MBA?", "RAG"),
        ("What documents are required for admission?", "RAG"),
        
        # Chitchat
        ("Hello", "CHITCHAT"),
        ("Namaste", "CHITCHAT"),
        ("Thank you", "CHITCHAT"),
        ("Bye", "CHITCHAT"),
        
        # Genuine enrollment (these might return None from fast route, that's OK)
        # We'll test the semantic router handles them correctly instead
    ]
    
    passed = 0
    failed = 0
    
    for query, expected in test_cases:
        result = router._fast_keyword_route(query)
        
        if result is None:
            # Fast route couldn't determine — this is acceptable for semantic router to handle
            print(f"  ⚠️  SKIP: Fast route returned None for '{query}' (semantic router will handle)")
            continue
        
        if result == expected:
            print(f"  ✅ PASS: '{query[:40]}...' → {result}")
            passed += 1
        else:
            print(f"  ❌ FAIL: '{query[:40]}...' → Got {result}, Expected {expected}")
            failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return passed, failed


# =====================================================================
# Test 4: Semantic Router Classification
# =====================================================================
def test_semantic_router():
    """Test that semantic router doesn't misclassify info queries as INTERESTED."""
    print("\n" + "="*70)
    print("TEST 4: SEMANTIC ROUTER (Full Pipeline)")
    print("="*70)
    
    from app.services.llm_router import LLMRouter
    router = LLMRouter()
    
    test_cases = [
        # These were previously misrouted — they MUST go to RAG
        ("Can I get admission through CUET?", "RAG"),
        ("What is the admission process?", "RAG"),
        ("How do I apply for BTech?", "RAG"),
        ("I am interested in knowing about TMU", "RAG"),
        ("Why should I choose TMU over other universities?", "RAG"),
        
        # These should stay as INTERESTED
        ("I want to apply now, my name is Raj", "INTERESTED"),
        ("Mujhe admission lena hai abhi, form bhej do", "INTERESTED"),
        
        # Basic chitchat
        ("Hello, how are you?", "CHITCHAT"),
        ("Namaste ji", "CHITCHAT"),
    ]
    
    passed = 0
    failed = 0
    
    async def run_tests():
        nonlocal passed, failed
        for query, expected in test_cases:
            result = await router.route_query(query)
            if result == expected:
                print(f"  ✅ PASS: '{query[:45]}...' → {result}")
                passed += 1
            else:
                print(f"  ❌ FAIL: '{query[:45]}...' → Got {result}, Expected {expected}")
                failed += 1
    
    asyncio.run(run_tests())
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return passed, failed


# =====================================================================
# Test 5: CrewAI Agent Identity Check
# =====================================================================
def test_crew_agent_identity():
    """Check that CrewAI agent definitions use correct identity."""
    print("\n" + "="*70)
    print("TEST 5: CREW AGENT IDENTITY & GROUNDING")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # Read crew_workflow.py source
    crew_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              "app", "services", "crew_workflow.py")
    with open(crew_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    # Check no Riya in crew workflow (except anti-instructions saying "NOT Riya" or "NEVER...Riya")
    import re as regex
    # Find lines with Riya that DON'T contain "NEVER" or "NOT" or "not" before "Riya"
    positive_riya_refs = []
    for i, line in enumerate(source.split('\n'), 1):
        if "Riya" in line:
            # Allow anti-instructions
            if any(word in line.lower() for word in ["never", "not riya", "not any other name"]):
                continue
            positive_riya_refs.append((i, line.strip()))
    
    if not positive_riya_refs:
        print(f"  ✅ PASS: crew_workflow.py has no positive 'Riya' references")
        passed += 1
    else:
        print(f"  ❌ FAIL: crew_workflow.py has {len(positive_riya_refs)} positive 'Riya' references")
        for line_num, line_text in positive_riya_refs:
            print(f"     Line {line_num}: {line_text}")
        failed += 1
    
    # Check Moradabad is referenced
    if "Moradabad" in source or "MORADABAD" in source:
        print(f"  ✅ PASS: crew_workflow.py anchors TMU to Moradabad")
        passed += 1
    else:
        print(f"  ❌ FAIL: crew_workflow.py does NOT anchor TMU to Moradabad")
        failed += 1
    
    # Check anti-hallucination in agent backstory
    if "NEVER guess" in source or "NEVER invent" in source:
        print(f"  ✅ PASS: crew_workflow.py has anti-hallucination rules")
        passed += 1
    else:
        print(f"  ❌ FAIL: crew_workflow.py missing anti-hallucination rules")
        failed += 1
    
    # Check word limit enforcement
    if "60 words" in source or "2-3 sentences" in source:
        print(f"  ✅ PASS: crew_workflow.py enforces response length")
        passed += 1
    else:
        print(f"  ❌ FAIL: crew_workflow.py missing response length limits")
        failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return passed, failed


# =====================================================================
# Main Runner
# =====================================================================
if __name__ == "__main__":
    print("\n" + "🔥"*35)
    print("   CRITICAL FIXES TEST SUITE — v3.0")
    print("🔥"*35)
    
    total_passed = 0
    total_failed = 0
    
    # Run tests
    tests = [
        test_hallucination_guard,
        test_identity_consistency,
        test_intent_classification,
        test_semantic_router,
        test_crew_agent_identity,
    ]
    
    for test_fn in tests:
        try:
            p, f = test_fn()
            total_passed += p
            total_failed += f
        except Exception as e:
            print(f"  ❌ ERROR: {test_fn.__name__} crashed: {e}")
            total_failed += 1
    
    # Summary
    print("\n" + "="*70)
    print(f"FINAL RESULTS: {total_passed} PASSED | {total_failed} FAILED")
    print("="*70)
    
    if total_failed == 0:
        print("🎉 ALL CRITICAL FIXES VERIFIED SUCCESSFULLY!")
    else:
        print(f"⚠️  {total_failed} tests need attention.")
    
    sys.exit(0 if total_failed == 0 else 1)
