import os
import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
AGENT_DIR = ROOT_DIR / "google-search-agent"

# Detect Python interpreter from virtual environments
venv_python = AGENT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    venv_python = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    venv_python = Path(sys.executable)

print("=" * 60)
print("🚀 Starting AI Search Agent Platform...")
print(f"Python interpreter: {venv_python}")
print("=" * 60)

# Start FastAPI backend
backend_cmd = [
    str(venv_python),
    "-m", "uvicorn",
    "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--reload"
]

print("\n1. Launching FastAPI Backend on http://127.0.0.1:8000 ...")
backend_proc = subprocess.Popen(
    backend_cmd,
    cwd=str(AGENT_DIR),
)

time.sleep(2)

# Start Streamlit frontend
streamlit_cmd = [
    str(venv_python),
    "-m", "streamlit",
    "run",
    str(ROOT_DIR / "streamlit_app.py"),
    "--server.port", "8501",
    "--server.headless", "false"
]

print("2. Launching Streamlit Frontend on http://localhost:8501 ...")
try:
    frontend_proc = subprocess.Popen(
        streamlit_cmd,
        cwd=str(ROOT_DIR),
    )
    print("\n✅ AI Search Agent services are running!")
    print("👉 Frontend: http://localhost:8501")
    print("👉 Backend API: http://127.0.0.1:8000")
    print("👉 API Docs: http://127.0.0.1:8000/docs")
    print("\nPress Ctrl+C to gracefully stop all services.")
    frontend_proc.wait()
except KeyboardInterrupt:
    print("\nShutting down AI Search Agent services...")
finally:
    backend_proc.terminate()
