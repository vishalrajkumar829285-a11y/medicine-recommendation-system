# CareCompass — Educational Healthcare Insight System

An intentionally conservative demo that collects symptoms and basic health context, highlights urgent symptoms, and gives general self-care and consultation guidance. It includes registration/login, an SQLite-backed personal history/dashboard, and downloadable educational PDF summaries. It does **not** diagnose disease, prescribe medication, or replace a clinician.

## Run locally

1. Start the API:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app:app --reload
   ```
2. In another terminal, start the UI:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open the local Vite URL (normally `http://localhost:5173`).

## Safety boundaries

- Emergency symptoms show an urgent-care warning instead of a routine result.
- No drug dosage or prescription generation is included.
- User records are stored locally in `backend/carecompass.db`. Use a secured database, protected tokens, encryption, consent controls, and clinical review before storing real health data in production.
