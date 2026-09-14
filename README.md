# Firebird AI – Knowledge-Trained AI Chatbot

A clean, responsive, knowledge-trained RAG (Retrieval-Augmented Generation) chatbot. Firebird AI answers questions strictly based on your uploaded documentation, technical Standard Operating Procedures (SOP), and approved Q&A dataset—citing exact documents, page numbers, and verified snippets without hallucination.

---

## Key Features

1. **Automatic Knowledge Updating (Zero Retraining / Zero Restart)**
   - Upload PDF, TXT, Markdown, CSV, or JSON documents.
   - Page-by-page PDF parsing automatically tracks page numbers (e.g., `Page 14`).
   - Add approved Q&A pairs directly.
   - Text chunks and vector embeddings are indexed into SQLite immediately and available on the very next query.

2. **Accurate Answers with Grounded Citations**
   - Retrieves top relevant knowledge chunks using cosine similarity.
   - Generates answers adhering to strict system rules:
     - *"Always prioritize retrieved knowledge over general assumptions."*
     - *"Do not invent facts."*
     - *"If the required information cannot be found in the knowledge base, clearly say that the information could not be found."*
   - Cites document name, page number, and snippet quotes.

3. **Conversation Memory**
   - Remembers past context in the conversation session (e.g. answering follow-ups like *"What should I check first?"*).

4. **Future Power BI Integration Readiness**
   - `POST /api/chat` accepts optional `report_context` (report name, visual title, active slicers/filters, data summary).
   - UI includes a Power BI Context Simulator to test grounded hybrid answers.

5. **ChatGPT-Style Modern UI**
   - Dark theme with Firebird ember accents, clean typography, responsive layout, and interactive Source Citations cards.

---

## Project Structure

```text
Data Chat/
├── backend/
│   ├── main.py            # FastAPI endpoints & CORS
│   ├── database.py        # SQLite schema (Docs, Chunks, Q&A, Chats, Messages)
│   ├── models.py          # Pydantic data schemas
│   ├── knowledge.py       # Ingestion, PDF page extractor & chunking
│   ├── embeddings.py      # Embedding generator (OpenAI API + fallback vectorizer)
│   ├── retrieval.py       # Vector cosine similarity search
│   ├── chat.py            # RAG orchestrator, conversational memory & prompt builder
│   ├── test_pipeline.py   # Backend verification test suite
│   └── requirements.txt   # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # Chat list, "+ New Chat", Knowledge Base button
│   │   │   ├── ChatArea.jsx         # Message thread, empty state prompt suggestions
│   │   │   ├── MessageItem.jsx      # Message bubble & expandable source citation drawer
│   │   │   ├── ChatInput.jsx        # Auto-resizing textarea with keyboard shortcuts
│   │   │   ├── KnowledgeModal.jsx   # Document uploader & Q&A manager
│   │   │   └── PowerBIModal.jsx     # Power BI report context simulator
│   │   ├── services/
│   │   │   └── api.js              # REST client for backend
│   │   ├── App.jsx
│   │   ├── index.css                # Dark mode styling with ember accents
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── data/
│   ├── knowledge/                   # Sample SOP files (Pressure SOP.pdf, Pressure_SOP.txt)
│   └── firebird.db                  # SQLite database
│
├── .env.example
├── .gitignore
└── README.md
```

---

## Quickstart Guide

### 1. Configure Environment (`.env`)
Copy the example file to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API provider:
```env
AI_API_KEY=your_api_key_here
AI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
AI_BASE_URL=https://api.openai.com/v1
PORT=8000
HOST=0.0.0.0
```
*(Supports OpenAI, Google Gemini OpenAI-compatible endpoint, OpenRouter, Groq, Ollama, etc. Also includes a deterministic built-in vectorizer if run offline).*

### 2. Run Backend
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI documentation is available at `http://localhost:8000/docs`.

### 3. Run Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send question, retrieve knowledge, generate answer with sources |
| `POST` | `/api/knowledge/upload` | Upload and immediately index PDF, TXT, MD, CSV, JSON |
| `POST` | `/api/knowledge/qa` | Directly index an approved Question + Answer pair |
| `GET` | `/api/knowledge` | List all indexed documents, chunk counts, and Q&A items |
| `DELETE` | `/api/knowledge/{id}` | Delete a document or Q&A pair and its embeddings |
| `POST` | `/api/chats` | Create a new conversation session |
| `GET` | `/api/chats` | List all conversation sessions |
| `GET` | `/api/chats/{id}` | Fetch full message history and cited sources |
| `DELETE` | `/api/chats/{id}` | Delete conversation |
| `GET` | `/api/health` | Service health status and knowledge base statistics |

---

## Testing Verification

Run the automated backend test pipeline:
```bash
python backend/test_pipeline.py
```
This tests:
1. Document ingestion and chunking (`Pressure SOP.pdf` page 14).
2. Q&A pair indexing.
3. Cosine similarity retrieval.
4. Answer generation with page citations.
5. Conversational memory follow-up questions.
6. Unknown query refusal (*"I couldn't find this information in the provided knowledge base"*).
7. Power BI context integration.
