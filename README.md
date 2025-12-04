# Medical Appointment Scheduling Agent

This project is an implementation of the assessment: a conversational agent to schedule medical appointments
using a mock Calendly API, a RAG FAQ system, and a FastAPI backend with a minimal React frontend.

## Structure
See project tree in the repository.

## Quick start
1. Create virtualenv and install:
   ```
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create data dir and ensure files exist:
   ```
   ls data
   ```

3. Start backend:
   ```
   uvicorn backend.main:app --reload --port 8000
   ```

4. Start frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```

5. Run tests:
   ```
   pytest -q
   ```
