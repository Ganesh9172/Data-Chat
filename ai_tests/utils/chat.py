import time
from typing import Optional, Dict, Any, List
from playwright.sync_api import Page, expect
from ai_tests.config import FIREBIRD_URL, TIMEOUT

# Primary and fallback selectors
SELECTORS = {
    "chat_input": '[data-testid="chat-input"], .chat-input-field, textarea[placeholder*="Ask questions"]',
    "send_btn": '[data-testid="send-btn"], button.send-btn',
    "new_chat_btn": '[data-testid="new-chat-btn"], button.refresh-btn',
    "loading_indicator": '[data-testid="loading-indicator"], .loading-card, .typing-dots-indicator',
    "user_message": '[data-testid="user-message"], .user-bubble',
    "ai_message": '[data-testid="ai-message"], .ai-card-content',
    "citation_box": '[data-testid="citation-box"], .source-citation-box',
    "ground_truth_badge": '[data-testid="ground-truth-badge"], .ground-truth-badge',
    "header_title": '.bot-name'
}

def open_firebird(page: Page, url: Optional[str] = None) -> None:
    """
    Opens the Firebird web application and waits for the interface to be ready.
    """
    target_url = url or FIREBIRD_URL
    page.goto(target_url, wait_until="domcontentloaded")
    # Wait for the chat input to be visible and ready
    page.wait_for_selector(SELECTORS["chat_input"], state="visible", timeout=TIMEOUT)
    # Ensure header is rendered
    try:
        page.wait_for_selector(SELECTORS["header_title"], state="visible", timeout=5000)
    except Exception:
        pass

def send_message(page: Page, message: str) -> int:
    """
    Enters a message into the chat input and clicks Send.
    Returns the count of existing AI messages prior to sending.
    """
    input_elem = page.locator(SELECTORS["chat_input"]).first
    input_elem.wait_for(state="visible", timeout=TIMEOUT)

    # Record current count of AI responses
    current_ai_count = page.locator(SELECTORS["ai_message"]).count()

    # Fill input and click send
    input_elem.fill(message)
    
    send_button = page.locator(SELECTORS["send_btn"]).first
    send_button.wait_for(state="visible", timeout=TIMEOUT)
    send_button.click()

    return current_ai_count

def wait_for_ai_response(
    page: Page,
    prev_ai_count: int,
    timeout: Optional[int] = None
) -> str:
    """
    Waits for the assistant to finish processing and return a complete response.
    Waits for:
    1. A new AI message element to appear (count == prev_ai_count + 1).
    2. Any loading indicator to disappear.
    Returns the text content of the latest assistant message.
    """
    max_wait = timeout or TIMEOUT
    start_time = time.time()

    # 1. Wait for message count to increment
    ai_messages = page.locator(SELECTORS["ai_message"])
    while time.time() - start_time < (max_wait / 1000):
        if ai_messages.count() > prev_ai_count:
            break
        page.wait_for_timeout(200)

    if ai_messages.count() <= prev_ai_count:
        raise TimeoutError(f"Assistant did not respond within {max_wait}ms")

    # 2. Wait for loading indicator to finish / detach if currently visible
    loading_loc = page.locator(SELECTORS["loading_indicator"])
    if loading_loc.count() > 0:
        try:
            loading_loc.first.wait_for(state="detached", timeout=max_wait)
        except Exception:
            pass

    # Give DOM a tiny settling moment for markdown rendering
    page.wait_for_timeout(300)

    latest_message = ai_messages.nth(ai_messages.count() - 1)
    return latest_message.inner_text().strip()

def get_latest_ai_message(page: Page) -> str:
    """Returns the text of the latest AI message."""
    messages = page.locator(SELECTORS["ai_message"])
    if messages.count() == 0:
        return ""
    return messages.nth(messages.count() - 1).inner_text().strip()

def get_latest_citations(page: Page) -> Optional[str]:
    """Returns the text of the latest citation box if present, or None."""
    citations = page.locator(SELECTORS["citation_box"])
    if citations.count() == 0:
        return None
    return citations.nth(citations.count() - 1).inner_text().strip()

def is_ground_truth_badge_visible(page: Page) -> bool:
    """Checks if the 'Ground-truth verified' badge is visible on the latest AI response."""
    # Find the badge in the last AI message row
    ai_rows = page.locator(".message-row.ai-row")
    if ai_rows.count() == 0:
        return False
    latest_row = ai_rows.nth(ai_rows.count() - 1)
    badge = latest_row.locator(SELECTORS["ground_truth_badge"])
    return badge.count() > 0 and badge.first.is_visible()

def start_new_chat(page: Page) -> None:
    """Clicks New Chat and waits for the message list to be reset."""
    btn = page.locator(SELECTORS["new_chat_btn"]).first
    if btn.is_visible():
        btn.click()
        page.wait_for_timeout(300)
