import json
import pytest
from pathlib import Path
from playwright.sync_api import Page
from ai_tests.config import TEST_DATA_DIR
from ai_tests.utils.chat import send_message, wait_for_ai_response, start_new_chat
from ai_tests.utils.evaluator import evaluate_response
from ai_tests.utils.report import global_report_collector

def load_followup_scenarios():
    data_file = TEST_DATA_DIR / "followups.json"
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)

scenarios = load_followup_scenarios()

@pytest.mark.parametrize("scenario", scenarios)
def test_followup_conversation(firebird_page: Page, scenario: dict):
    """
    Tests multi-turn conversations to verify that Firebird maintains conversation context.
    """
    start_new_chat(firebird_page)
    turns = scenario.get("turns", [])
    scenario_id = scenario.get("id", "unknown")

    print(f"\n[Testing Follow-up Scenario]: {scenario_id}")

    for idx, turn in enumerate(turns):
        question = turn["question"]
        expected = turn["expected_meaning"]

        print(f"  Turn {idx + 1}: '{question}'")
        prev_count = send_message(firebird_page, question)

        response = wait_for_ai_response(firebird_page, prev_count)
        print(f"  Response {idx + 1}: {response[:120]}...")

        eval_result = evaluate_response(
            question=question,
            expected_meaning=expected,
            actual_response=response,
            category="followup"
        )

        passed = eval_result["pass"]
        reason = eval_result["reason"]

        global_report_collector.record(
            category="followup",
            question=f"[{scenario_id} T{idx+1}] {question}",
            expected=expected,
            actual=response[:200] + ("..." if len(response) > 200 else ""),
            passed=passed,
            reason=reason
        )

        assert passed, f"Turn {idx + 1} ('{question}') failed in scenario {scenario_id}: {reason}"
