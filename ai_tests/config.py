import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent

# Load .env if present in ai_tests or project root
env_ai_tests = TESTS_DIR / ".env"
env_root = PROJECT_ROOT / ".env"
if env_ai_tests.exists():
    load_dotenv(env_ai_tests, override=False)
elif env_root.exists():
    load_dotenv(env_root, override=False)

# Configuration values with safe defaults
FIREBIRD_URL = os.getenv("FIREBIRD_URL", "http://localhost:5173").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Playwright settings
HEADLESS_STR = os.getenv("HEADLESS", "false").lower()
HEADLESS = HEADLESS_STR in ("true", "1", "yes")

TIMEOUT = int(os.getenv("TIMEOUT", "60000"))
SLOWMO = int(os.getenv("SLOWMO", "0"))

# Evaluator settings
AI_EVALUATOR_ENABLED = os.getenv("AI_EVALUATOR_ENABLED", "false").lower() in ("true", "1", "yes")
AI_EVALUATOR_PROVIDER = os.getenv("AI_EVALUATOR_PROVIDER", "ollama").lower()
AI_EVALUATOR_MODEL = os.getenv("AI_EVALUATOR_MODEL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# Directory structure
TEST_DATA_DIR = TESTS_DIR / "test_data"
REPORTS_DIR = TESTS_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

# Ensure reports directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
