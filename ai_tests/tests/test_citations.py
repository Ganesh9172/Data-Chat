import json
import pytest
from pathlib import Path
from playwright.sync_api import Page
from ai_tests.config import TEST_DATA_DIR
from ai_tests.utils.chat import (
    send_message,
    wait_for_ai_response,
    get_latest_citations,
    is_ground_truth_badge_visible,
    start_new_chat
)
from ai_tests.utils.evaluator import evaluate_response
from ai_tests.utils.report import global_report_collector

def load_citation_tests():
    data_file = TEST_DATA_DIR / "citation_tests.json"
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)

citation_cases = load_citation_tests()

@pytest.mark.parametrize("case", citation_cases)
def test_knowledge_and_citations(firebird_page: Page, case: dict):
    """
    Tests questions that should use Firebird technical documents:
    - Response exists and is not empty.
    - Ground-truth badge or citation/source element is displayed.
    - Document source information is present.
    - If citation exists, checks whether relevant keywords/pages are mentioned.
    """
    start_new_chat(firebird_page)

    case_id = case.get("id", "citation_test")
    question = case["question"]
    expected_meaning = case.get("expected_meaning", "")
    expect_cit = case.get("expect_citation", True)
    expected_keywords = case.get("expected_source_keywords", [])

    print(f"\n[Testing Citations] ({case_id}): '{question}'")
    prev_count = send_message(firebird_page, question)

    response = wait_for_ai_response(firebird_page, prev_count)
    assert response and len(response.strip()) > 0, "Response must not be empty"

    # Check citation elements
    citation_text = get_latest_citations(firebird_page)
    badge_visible = is_ground_truth_badge_visible(firebird_page)

    print(f"  Response: {response[:120]}...")
    print(f"  Ground-truth badge visible: {badge_visible}")
    print(f"  Citation text: {citation_text}")

    # Evaluate semantic answer content
    eval_result = evaluate_response(
        question=question,
        expected_meaning=expected_meaning,
        actual_response=response,
        category="citations"
    )

    citation_valid = True
    citation_note = ""

    if expect_cit:
        if not citation_text and not badge_visible:
            citation_valid = False
            citation_note = "Expected citation or ground-truth badge, but neither was displayed."
        elif citation_text:
            # Check for document keyword presence
            cit_lower = citation_text.lower()
            keyword_found = any(kw.lower() in cit_lower for kw in expected_keywords)
            if not keyword_found:
                # Mark for manual review per requirements
                citation_note = f"Citation present ('{citation_text}') but keywords {expected_keywords} not immediately found - flagged for manual review."
            else:
                citation_note = f"Citation verified: {citation_text}"
        else:
            citation_note = "Ground-truth verified badge active."

    overall_pass = eval_result["pass"] and (not expect_cit or (citation_text or badge_visible))
    reason = f"Answer: {eval_result['reason']}. Citation: {citation_note}"

    global_report_collector.record(
        category="citations",
        question=question,
        expected=f"{expected_meaning} (Citation expected: {expect_cit})",
        actual=f"{response[:140]}... | Citations: {citation_text or ('Badge only' if badge_visible else 'None')}",
        passed=overall_pass,
        reason=reason
    )

    assert overall_pass, f"Citation test failed for '{question}': {reason}"
