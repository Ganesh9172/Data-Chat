import json
import pytest
from pathlib import Path
from playwright.sync_api import Page
from ai_tests.config import TEST_DATA_DIR
from ai_tests.utils.chat import send_message, wait_for_ai_response, start_new_chat
from ai_tests.utils.evaluator import evaluate_response
from ai_tests.utils.report import global_report_collector

def load_natural_language_variations():
    data_file = TEST_DATA_DIR / "natural_language.json"
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cases = []
    for item in data:
        base = item.get("base_question", "")
        expected = item.get("expected_meaning", "")
        for var in item.get("variations", []):
            cases.append((var, expected))
    return cases

variations = load_natural_language_variations()

@pytest.mark.parametrize("question,expected_meaning", variations)
def test_natural_language_variation(firebird_page: Page, question: str, expected_meaning: str):
    """
    Tests whether Firebird understands different human ways of asking the same question.
    """
    # Start fresh chat session
    start_new_chat(firebird_page)

    print(f"\n[Testing Natural Language] Question: '{question}'")
    prev_count = send_message(firebird_page, question)

    response = wait_for_ai_response(firebird_page, prev_count)
    print(f"[Response]: {response[:150]}...")

    eval_result = evaluate_response(
        question=question,
        expected_meaning=expected_meaning,
        actual_response=response,
        category="natural_language"
    )

    passed = eval_result["pass"]
    reason = eval_result["reason"]

    global_report_collector.record(
        category="natural_language",
        question=question,
        expected=expected_meaning,
        actual=response[:200] + ("..." if len(response) > 200 else ""),
        passed=passed,
        reason=reason
    )

    assert passed, f"Evaluation failed for '{question}': {reason}"
