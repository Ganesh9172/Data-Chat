# Firebird AI - Playwright Automated Testing Suite

This is an independent automated testing suite for **Firebird AI** built with **Python**, **pytest**, and **Playwright**.

It operates completely outside of Firebird's core code, preserving the existing JSON storage system, RAG pipeline, and React frontend without introducing any database or modifying backend logic.

---

## 📁 Directory Structure

```
ai_tests/
├── README.md                  # Documentation and guide
├── requirements.txt           # Python test dependencies
├── .env.example               # Example configuration file
├── config.py                  # Test configuration and environment loading
├── conftest.py                # Pytest fixtures and failure screenshot hooks
│
├── tests/                     # Test Suites
│   ├── test_basic.py          # Test 1: Browser launch & UI verification
│   ├── test_chat.py           # Test 2: Real question & empty input handling
│   ├── test_natural_language.py # Natural language variations (e.g. 0.5 bar)
│   ├── test_general_questions.py# Greetings, identity, date/time questions
│   ├── test_followups.py      # Multi-turn conversational context
│   ├── test_out_of_scope.py   # Hallucination prevention for out-of-scope queries
│   └── test_citations.py      # Document sources and ground-truth verification
│
├── test_data/                 # Pure JSON Test Datasets
│   ├── natural_language.json  # Phrasing variations for core questions
│   ├── knowledge_questions.json# Document-based technical questions
│   ├── general_questions.json # Conversational & date/time test cases
│   ├── followups.json         # Multi-turn conversation scripts
│   ├── out_of_scope.json      # Unrelated questions (sports, pricing, etc.)
│   └── citation_tests.json    # Questions expecting document citations
│
├── utils/                     # Test Helpers & Evaluator
│   ├── browser.py             # Playwright Chromium browser manager
│   ├── chat.py                # Chat interaction & DOM response waiting
│   ├── evaluator.py           # Semantic evaluator (Deterministic & optional Ollama)
│   ├── report.py              # Test report aggregator (Terminal, Markdown, JSON)
│   └── generator.py           # AI natural language test case generator
│
└── reports/                   # Test Outputs & Artifacts
    ├── test_report.md         # Generated Markdown report summary
    ├── test_report.json       # Machine-readable test results
    └── screenshots/           # Automatic failure screenshots
```

---

## 🛠️ Installation

1. Install Python test dependencies:
   ```bash
   pip install -r ai_tests/requirements.txt
   ```

2. Install Playwright's Chromium browser:
   ```bash
   playwright install chromium
   ```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` (or configure via environment variables):
```bash
cp ai_tests/.env.example ai_tests/.env
```

Key configuration parameters (`ai_tests/config.py`):
| Variable | Default | Description |
| :--- | :--- | :--- |
| `FIREBIRD_URL` | `http://localhost:5173` | Local Firebird React frontend URL |
| `BACKEND_URL` | `http://localhost:8000` | Local FastAPI backend URL |
| `HEADLESS` | `false` | Set to `true` for headless mode or `false` to watch browser |
| `TIMEOUT` | `30000` | Default element / response timeout in milliseconds |
| `SLOWMO` | `0` | Delay between Playwright actions in milliseconds |
| `AI_EVALUATOR_ENABLED` | `false` | Enable local Ollama LLM evaluation (`true`/`false`) |
| `AI_EVALUATOR_PROVIDER`| `ollama` | Provider for optional AI evaluator |
| `AI_EVALUATOR_MODEL` | `llama3.2` | Local model name for Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama local API base URL |

---

## 🚀 Running Firebird AI (Application)

Before running the Playwright tests, start your existing local servers:

1. **Backend (FastAPI)**:
   ```powershell
   cd backend
   uvicorn main:app --reload --port 8000
   ```
2. **Frontend (React/Vite)**:
   ```powershell
   cd frontend
   npm run dev
   ```

---

## 🧪 Running Tests

### 1. Run Basic Test (Launch browser & verify interface)
```bash
pytest ai_tests/tests/test_basic.py -v -s
```

### 2. Run Chat Test (Send real question "Is 0.5 bar okay?" & check response)
```bash
pytest ai_tests/tests/test_chat.py -v -s
```

### 3. Run Natural Language Variation Tests
```bash
pytest ai_tests/tests/test_natural_language.py -v -s
```

### 4. Run General & Date/Time Tests
```bash
pytest ai_tests/tests/test_general_questions.py -v -s
```

### 5. Run Follow-up Context Tests
```bash
pytest ai_tests/tests/test_followups.py -v -s
```

### 6. Run Citation Verification Tests
```bash
pytest ai_tests/tests/test_citations.py -v -s
```

### 7. Run All Tests
```bash
pytest ai_tests/tests/ -v -s
```

---

## 📊 Test Reports & Failure Screenshots

- **Terminal Report**: An ASCII summary of pass/fail counts grouped by category is printed after each test session.
- **Markdown Report**: Saved to `ai_tests/reports/test_report.md`.
- **JSON Report**: Saved to `ai_tests/reports/test_report.json`.
- **Failure Screenshots**: If any test fails, Playwright automatically saves a full-page screenshot to `ai_tests/reports/screenshots/fail_<test_name>_<timestamp>.png`.

---

## ➕ Adding New JSON Test Cases

Because Firebird uses JSON storage, all automated test cases are also maintained in pure JSON format under `ai_tests/test_data/`.

To add a new natural language test case, open `ai_tests/test_data/natural_language.json` and append an entry:

```json
{
  "id": "nl_radiator_cold",
  "category": "natural_language",
  "base_question": "Why is my radiator cold at the top?",
  "expected_meaning": "Trapped air in the radiator which requires bleeding.",
  "variations": [
    "top of radiator is freezing",
    "radiator cold up top hot at bottom",
    "air in radiator symptoms",
    "why radiator not heating evenly"
  ]
}
```

Then simply re-run `pytest ai_tests/tests/test_natural_language.py -v -s`.

---

## 🤖 Generating Natural Language Variations

You can generate variations for any base question using the built-in generator utility:

```bash
python -m ai_tests.utils.generator "Is 0.5 bar okay?"
```

This generates realistic human variations including typos, casual phrasing, and different sentence structures.
