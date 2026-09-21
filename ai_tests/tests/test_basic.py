import pytest
from playwright.sync_api import Page, expect
from ai_tests.utils.chat import SELECTORS, open_firebird
from ai_tests.utils.report import global_report_collector

def test_open_firebird_and_verify_interface(firebird_page: Page):
    """
    Test 1: Launch Chromium, open Firebird frontend, wait for load,
    verify chat interface, input, and send button are present and visible.
    """
    # Verify chat input exists and is visible
    chat_input = firebird_page.locator(SELECTORS["chat_input"]).first
    expect(chat_input).to_be_visible()

    # Verify send button exists
    send_btn = firebird_page.locator(SELECTORS["send_btn"]).first
    expect(send_btn).to_be_visible()

    # Verify placeholder text
    placeholder = chat_input.get_attribute("placeholder") or ""
    assert "ask" in placeholder.lower() or "firebird" in placeholder.lower() or len(placeholder) > 0

    # Record in report collector
    global_report_collector.record(
        category="basic",
        question="Load Firebird UI",
        expected="Chat input and send button should be visible",
        actual=f"Interface loaded successfully. Input placeholder: '{placeholder}'",
        passed=True,
        reason="Chat interface rendered correctly"
    )
    print("\n[PASS] Firebird UI loaded successfully. Chat input is visible and ready.")
