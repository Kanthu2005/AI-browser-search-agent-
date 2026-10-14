# AI Search Agent 🔍

A premium, responsive AI-powered research assistant inspired by **Perplexity**, **Google Search**, and **Linear**. It performs real-time web research, synthesizes clear structured answers, and extracts verified source citations.

---

## 🚀 Key Features

- **Live Web Research**: Uses Groq API's browser search tools (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) to search and open real-world web pages.
- **Verified Source Citations**: Automatically extracts domain names, titles, and direct external links (`target="_blank"`).
- **Modern UI & Aesthetic**:
  - Clean light theme (`#F8FAFC`) with dark theme toggle support.
  - Linear/Perplexity-inspired card layout, Inter typography, and subtle shadows.
  - Quick query chips for instant research questions.
- **Dual-Mode Reliability**:
  - **Connected Mode**: Communicates with the FastAPI backend at `http://127.0.0.1:8000/search`.
  - **Direct Mode**: Fallback execution directly via Groq client if the backend server is offline.
- **Session History**: Track, review, and clear previous research questions and answers.
- **One-Click Launcher**: Easily launch both frontend and backend using `run.bat` or `python start_app.py`.

---

## 🛠️ Tech Stack & Response Contract

- **Frontend**: Streamlit, Custom Responsive CSS
- **Backend**: FastAPI, Uvicorn, Pydantic, Dotenv
- **AI Engine**: Groq API (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`)

### API Contract (`POST /search`):
```json
{
  "question": "Who won the 2024 IPL final?",
  "answer": "The 2024 Indian Premier League (IPL) was won by Kolkata Knight Riders...",
  "sources": [
    {
      "title": "2024 Indian Premier League final",
      "url": "https://en.wikipedia.org/wiki/2024_Indian_Premier_League_final"
    }
  ],
  "status": "success",
  "model_used": "openai/gpt-oss-120b"
}
```

---

## 📦 Installation & Setup

1. **Activate Virtual Environment**:
   ```powershell
   & "google-search-agent/venv/Scripts/Activate.ps1"
   ```

2. **Configure API Key**:
   Ensure `GROQ_API_KEY` is present in `.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

---

## 🏃 Running the Application

### Option A: One-Click Runner (Recommended)
Double-click `run.bat` or run:
```powershell
python start_app.py
```

### Option B: Run Services Manually

**Terminal 1 — FastAPI Backend:**
```powershell
cd google-search-agent
& "venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Streamlit Frontend:**
```powershell
& "google-search-agent/venv/Scripts/python.exe" -m streamlit run streamlit_app.py --server.port 8501
```

- **Frontend URL**: `http://localhost:8501`
- **Backend API**: `http://127.0.0.1:8000`
- **Swagger Docs**: `http://127.0.0.1:8000/docs`
