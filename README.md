# PDF-QA Validation Portal

A modern web application built to help QA teams validate PDF-to-HTML parsing pipelines. It features side-by-side visualization of original PDFs and parsed HTML, section-by-section TOC navigation, full-text FTS5 database searching, footnote/comment validation, annotations/highlights persistence, and QA report exporting (JSON/CSV).

## Features

- **Side-by-Side Sync View**: PDF original canvas and parsed HTML content view side-by-side with synchronized zoom and scroll capabilities.
- **TOC & Section Navigation**: Interactive Sidebar listing chapters, schedules, parts, divisions, and sections.
- **Full-Text Search (FTS5)**: Fast local SQLite database query search covering all sections.
- **Review & Validation Workflow**: Flag sections or approve them, and manage review statuses.
- **Inline Highlights & Annotations**: Highlight any text in the HTML view and save notes/annotations.
- **Footnote / Marker Management**: Verify inline footnote mappings page-by-page.
- **QA Report Exporting**: Stream summary reports as downloadable JSON or CSV files.

---

## Technical Stack

- **Backend**: Python 3.11, FastAPI, SQLite (FTS5 indexation), `pypdf`, `aiosqlite`, `uvicorn`.
- **Frontend**: Vite, React 18, Zustand (State Management), Vanilla CSS (Modern CSS grid, HSL palettes, Glassmorphism design).
- **Dockerization**: Fully containerized using multi-service Docker Compose configurations.

---

## Getting Started

### Option A: Run with Docker Compose (Recommended)

1. Make sure you have **Docker Desktop** installed and running on your system.
2. Build and start the services from the repository root:
   ```bash
   docker compose up -d --build
   ```
3. Open your browser and navigate to:
   - **Frontend Dashboard**: [http://localhost:5173/](http://localhost:5173/)
   - **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
4. Persistent database state and upload assets will map directly to `./backend/data` and `./backend/uploads` respectively on your host machine.

To stop the application:
```bash
docker compose down
```

### Option B: Local Setup (Manual)

#### Prerequisites
- Node.js 18+
- Python 3.10+

#### 1. Setup Backend
```bash
cd backend
python -D venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py  # Seed the initial Income Tax Ordinance database records
uvicorn main:app --host 127.0.0.1 --port 8000
```

#### 2. Setup Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```
Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) to access the portal.
