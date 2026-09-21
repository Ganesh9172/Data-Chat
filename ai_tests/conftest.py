import sys
from pathlib import Path

# Ensure workspace root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
from ai_tests.config import HEADLESS, SLOWMO, TIMEOUT, FIREBIRD_URL
from ai_tests.utils.browser import create_browser_and_page, capture_failure_screenshot
from ai_tests.utils.chat import open_firebird
from ai_tests.utils.report import global_report_collector

@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="function")
def firebird_browser(playwright_instance: Playwright):
    browser, context, page = create_browser_and_page(
        playwright_instance,
        headless=HEADLESS,
        slow_mo=SLOWMO
    )
    yield browser, context, page
    try:
        page.close()
        context.close()
        browser.close()
    except Exception:
        pass

@pytest.fixture(scope="function")
def firebird_page(firebird_browser) -> Page:
    browser, context, page = firebird_browser
    open_firebird(page, FIREBIRD_URL)
    return page

@pytest.fixture(scope="session")
def report_collector():
    return global_report_collector

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # Capture screenshots only for failed test calls
    if rep.when == "call" and rep.failed:
        # Check if page is in funcargs
        page = None
        if "firebird_page" in item.funcargs:
            page = item.funcargs["firebird_page"]
        elif "firebird_browser" in item.funcargs:
            _, _, page = item.funcargs["firebird_browser"]

        if page:
            try:
                screenshot_path = capture_failure_screenshot(page, item.name, str(rep.longrepr))
                # Attach to test outcome if supported or record in collector
                rep.sections.append(("Failure Screenshot", str(screenshot_path)))
            except Exception as e:
                print(f"\n[Screenshot Capture Error]: {e}")

def pytest_sessionfinish(session, exitstatus):
    """
    Hook executed after all tests finish. Prints terminal summary and saves JSON/Markdown reports.
    """
    if len(global_report_collector.results) > 0:
        global_report_collector.print_summary()
        global_report_collector.save_reports()
