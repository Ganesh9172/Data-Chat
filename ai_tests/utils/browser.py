import time
import re
from pathlib import Path
from typing import Optional
from playwright.sync_api import Page, Browser, Playwright, BrowserContext
from ai_tests.config import HEADLESS, SLOWMO, TIMEOUT, SCREENSHOTS_DIR

def create_browser_and_page(
    playwright: Playwright,
    headless: Optional[bool] = None,
    slow_mo: Optional[int] = None
) -> tuple[Browser, BrowserContext, Page]:
    """
    Launches Chromium browser and initializes a new page with standard viewport.
    """
    is_headless = HEADLESS if headless is None else headless
    delay = SLOWMO if slow_mo is None else slow_mo

    browser = playwright.chromium.launch(
        headless=is_headless,
        slow_mo=delay,
        args=["--disable-dev-shm-usage", "--no-sandbox"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        device_scale_factor=1.0
    )
    page = context.new_page()
    page.set_default_timeout(TIMEOUT)
    return browser, context, page

def capture_failure_screenshot(
    page: Page,
    test_name: str,
    reason: Optional[str] = None
) -> Path:
    """
    Saves a screenshot when a test fails.
    File name contains sanitized test name and timestamp.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    sanitized = re.sub(r"[^\w\-_\.]", "_", test_name)[:50]
    timestamp = int(time.time())
    file_path = SCREENSHOTS_DIR / f"fail_{sanitized}_{timestamp}.png"
    try:
        page.screenshot(path=str(file_path), full_page=True)
        print(f"\n[Screenshot Saved] -> {file_path}")
    except Exception as e:
        print(f"\n[Screenshot Warning] Could not take screenshot: {e}")
    return file_path
