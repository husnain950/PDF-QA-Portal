# PDF-QA Validation Portal

A modern web application built to help QA teams validate PDF-to-HTML parsing pipelines. It features side-by-side visualization of original PDFs and parsed HTML, section-by-section TOC navigation, full-text FTS5 database searching, footnote/comment validation, annotations/highlights persistence, and QA report exporting (JSON/CSV).

## Features

- **Side-by-Side Sync View**: PDF original canvas and parsed HTML content view side-by-side with synchronized zoom and scroll capabilities.
- **TOC & Section Navigation**: Interactive Sidebar listing chapters, schedules, parts, divisions, and sections.
- **Corpus-scale navigation**: Dashboard source/title filters, TOC quick filtering, active-section scrolling, and `J`/`K` shortcuts.
- **Bounded PDF rendering**: Section mode renders one selected page at a time—even for very large page ranges—with `[`/`]` navigation.
- **Source fidelity views**: Compare rendered HTML, punctuation-faithful plain text, raw HTML, and raw JSON.
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

### Sync the ACT corpus

The repository does not contain the Acts-Discovery corpus. The repeatable sync
copies validated, content-addressed PDF/JSON files into ignored runtime storage
and records source hashes in the normal SQLite database. Existing uploads and QA
state remain intact.

Run a read-only audit first:

```bash
backend/venv/bin/python -m backend.sync_acts \
  --source /Users/muhammad.husnain/Documents/Claude/Projects/scratch/Cdx/Acts-Discovery/export \
  --dry-run
```

Then import into `backend/data` and `backend/uploads`:

```bash
backend/venv/bin/python -m backend.sync_acts \
  --source /Users/muhammad.husnain/Documents/Claude/Projects/scratch/Cdx/Acts-Discovery/export
```

An identical second run reports every unchanged source as `skipped`. Updates
run in one transaction per document. If a removed or changed leaf contains
annotations, or a removed leaf has completed review state, that document update
is rejected so evidence is not silently deleted.

### Option A: Run with Docker Compose

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
python -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

#### 2. Setup Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```
Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) to access the portal.

## Verification

Install the development test dependencies and run the complete checks:

```bash
backend/venv/bin/pip install -r backend/requirements-dev.txt
backend/venv/bin/python -m pytest -q backend/tests
backend/venv/bin/ruff check backend

cd frontend
npm install
npm test
npm run lint
npm run build
```
