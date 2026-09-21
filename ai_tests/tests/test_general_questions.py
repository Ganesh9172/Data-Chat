import json
import pytest
from pathlib import Path
from playwright.sync_api import Page
from ai_tests.config import TEST_DATA_DIR
from ai_tests.utils.chat import send_message, wait_for_ai_response, start_new_chat
from ai_tests.utils.evaluator import evaluate_response
from ai_tests.utils.report import global_report_collector

def load_general_questions():
    data_file = TEST_DATA_DIR / "general_questions.json"
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [(item["id"], item["question"], item["expected_meaning"]) for item in data]

general_test_cases = load_general_questions()

@pytest.mark.parametrize("case_id,question,expected_meaning", general_test_cases)
def test_general_question(firebird_page: Page, case_id: str, question: str, expected_meaning: str):
    """
    Tests general questions and date/time questions to ensure they are answered
    directly and conversationally, and not falsely routed to PDF document refusal.
    """
    start_new_chat(firebird_page)

    print(f"\n[Testing General Question] ({case_id}): '{question}'")
    prev_count = send_message(firebird_page, question)

    response = wait_for_ai_response(firebird_page, prev_count)
    print(f"[Response]: {response[:150]}...")

    eval_result = evaluate_response(
        question=question,
        expected_meaning=expected_meaning,
        actual_response=response,
        category="general_questions"
    )

    passed = eval_result["pass"]
    reason = eval_result["reason"]

    global_report_collector.record(
        category="general_questions",
        question=question,
        expected=expected_meaning,
        actual=response[:200] + ("..." if len(response) > 200 else ""),
        passed=passed,
        reason=reason
    )

    assert passed, f"General question evaluation failed for '{question}': {reason}"
