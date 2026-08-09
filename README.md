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
- **Static PDFs, versioned JSON**: the source PDF is stored once by content hash; each corrected parse lands as a new version with a leaf-level diff, a carry-over report, and one-click rollback.
- **Pipeline health**: per-document invariant and conservation badges, read from the Acts_fbr gate rather than recomputed.
- **Findings survive re-parses**: an annotation on a leaf the pipeline rewrote is re-anchored automatically, or flagged for recheck — it never blocks the fix and is never silently dropped.

---

## Technical Stack

- **Backend**: Python 3.11, FastAPI, SQLite (FTS5 indexation), `pypdf`, `aiosqlite`, `uvicorn`.
- **Frontend**: Vite, React 18, Zustand (State Management), Vanilla CSS (Modern CSS grid, HSL palettes, Glassmorphism design).
- **Dockerization**: Fully containerized using multi-service Docker Compose configurations.

---

## Getting Started

### How a document works here

A document is **one static PDF plus an ordered history of JSON parses of it**. The PDF
is uploaded (or synced) once and never re-sent; when the conversion pipeline is fixed,
push only the new JSON and it becomes the next *version*. Every version records what it
cost in review state, can be compared leaf-by-leaf against the previous one, and can be
rolled back.

Storage is content-addressed — `backend/uploads/pdf/<sha256>.pdf` and
`backend/uploads/json/<sha256>.json` — so the same source PDF shared by several
documents is stored once, and an unchanged JSON produces no new version at all.

### Sync the ACT corpus from the Acts_fbr pipeline

Point the sync straight at the pipeline repository. It pairs every corpus JSON
(`output/*.json`) with the PDF named in its own `metadata.filename` under `Acts/**`,
detecting PDFs by magic bytes because several corpus sources carry no `.pdf` suffix.

Read-only audit first:

```bash
.venv/bin/python -m backend.sync_acts \
  --acts-repo /Users/muhammad.husnain/Downloads/code/CC-FBR/Acts_fbr \
  --dry-run
```

Then import:

```bash
.venv/bin/python -m backend.sync_acts \
  --acts-repo /Users/muhammad.husnain/Downloads/code/CC-FBR/Acts_fbr
```

An identical second run reports every unchanged edition as `skipped`. A changed JSON
lands as that document's next version; reviewer findings on changed leaves are
re-anchored, findings on leaves the new parse dropped are kept as *orphaned* with a
snapshot of what they pointed at, and the whole tally is stored on the version and shown
in the portal's **Versions** panel.

A leaf whose declared pages cannot exist in the PDF is flagged
`page_range_out_of_bounds` rather than rejecting the edition — two live corpus editions
carry such leaves. `--strict` restores the old all-or-nothing behaviour (abort the run
on any problem, and refuse any ingest that would supersede reviewer state); use it in CI.

The legacy `--source DIR` layout (one folder per Act, each with one PDF and one JSON) is
still supported.

### Pipeline QA metrics

The portal never recomputes the pipeline's gate — it reads the numbers the pipeline
itself produced. Generate them in the Acts_fbr repository:

```bash
# invariants + regression cases, over every edition (fast)
python scripts/run_tests.py --json reports/qa-invariants.json

# body/footnote conservation (slow: re-reads every source PDF)
python scripts/audit_all.py --json reports/qa-conservation.json
```

Then ingest them:

```bash
.venv/bin/python -m backend.sync_acts --acts-repo <Acts_fbr> --metrics
```

Both reports are optional; a missing one is skipped, never an error. Results appear as
per-document health badges on the dashboard and per-version metrics (plus the delta
between versions) in the Versions panel.

### Seeding storage

**Neither the source PDFs nor the seed database are carried in git**, and both were
purged from history on 2026-08-09 — they were 806 MB of a repository whose actual source
is 5 MB, and the PDFs never change. A fresh clone therefore starts with no documents.
Populate a deployment once, by either:

```bash
# a) copy an existing store onto the volume (database + PDFs)
rsync -a backend/data/    <server>:/path/to/backend/data/
rsync -a backend/uploads/ <server>:/path/to/backend/uploads/

# b) or rebuild the ACT corpus from the pipeline (starts from an empty database)
.venv/bin/python -m backend.sync_acts --acts-repo <Acts_fbr>
```

Option (b) rebuilds the 80 ACT-corpus documents but not the manually uploaded Income Tax
Ordinance editions; use (a) to carry those, or re-upload them through the portal.
`backend/seed_data/qa_portal.db` and `backend/seed_uploads/` are still honoured at boot
when present, so dropping files there is a third way in — they are just no longer shipped.

Then confirm every document resolves to a readable PDF:

```bash
.venv/bin/python -m backend.audit_pdf_serving   # expects zero missing_file
```

Databases seeded from before content addressing are migrated automatically on boot; the
same migration can be run by hand, and previews itself first:

```bash
.venv/bin/python -m backend.migrate_blobs --dry-run
.venv/bin/python -m backend.migrate_blobs
.venv/bin/python -m backend.migrate_blobs --prune-orphans   # optional cleanup
```

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
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/python -m pytest -q backend/tests
.venv/bin/ruff check backend

# module self-checks
.venv/bin/python -m backend.services.blob_store
.venv/bin/python -m backend.services.anchoring
.venv/bin/python -m backend.services.versions
.venv/bin/python -m backend.services.acts_metrics

cd frontend
npm install
npm test
npm run lint
npm run build
```
