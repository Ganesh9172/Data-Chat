import pytest
from playwright.sync_api import Page, expect
from ai_tests.utils.chat import (
    SELECTORS,
    send_message,
    wait_for_ai_response,
    get_latest_ai_message,
    start_new_chat
)
from ai_tests.utils.evaluator import evaluate_response
from ai_tests.utils.report import global_report_collector

def test_send_real_question_pressure(firebird_page: Page):
    """
    Test 2: Send 'Is 0.5 bar okay?', wait for assistant response,
    detect completion, capture and print response, verify non-empty.
    """
    question = "Is 0.5 bar okay?"
    print(f"\n[Test Chat] Sending question: '{question}'")

    # Send message and track previous AI response count
    prev_count = send_message(firebird_page, question)

    # Wait for response completion using Playwright waiting mechanisms
    response = wait_for_ai_response(firebird_page, prev_count)

    # Print captured response
    print("\n" + "=" * 60)
    print(f"[Captured AI Response for '{question}']:\n{response}")
    print("=" * 60)

    # Verify response is not empty
    assert response and len(response.strip()) > 0, "Assistant returned an empty response"

    # Evaluate semantic meaning
    expected_desc = "The response should correctly explain whether 0.5 bar is within the documented pressure range."
    eval_result = evaluate_response(
        question=question,
        expected_meaning=expected_desc,
        actual_response=response,
        category="knowledge"
    )

    global_report_collector.record(
        category="knowledge",
        question=question,
        expected=expected_desc,
        actual=response[:200] + ("..." if len(response) > 200 else ""),
        passed=eval_result["pass"],
        reason=eval_result["reason"]
    )

    assert eval_result["pass"], f"Evaluation failed: {eval_result['reason']}"

def test_empty_input_behavior(firebird_page: Page):
    """
    Verifies that sending an empty message or whitespace does not trigger an empty AI message.
    """
    input_elem = firebird_page.locator(SELECTORS["chat_input"]).first
    input_elem.fill("   ")

    # Send button should either be disabled or clicking it does nothing
    send_btn = firebird_page.locator(SELECTORS["send_btn"]).first
    is_disabled = send_btn.is_disabled()

    initial_ai_count = firebird_page.locator(SELECTORS["ai_message"]).count()

    if not is_disabled:
        send_btn.click()
        firebird_page.wait_for_timeout(500)

    new_ai_count = firebird_page.locator(SELECTORS["ai_message"]).count()
    assert new_ai_count == initial_ai_count, "Empty input should not create a new AI message"

    global_report_collector.record(
        category="basic",
        question="<whitespace input>",
        expected="Send blocked or disabled",
        actual=f"Disabled: {is_disabled}, AI message count unchanged",
        passed=True,
        reason="Empty input handled gracefully"
    )
