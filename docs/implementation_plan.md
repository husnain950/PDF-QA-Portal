# PDF-QA Validation Portal — Implementation Plan

This document outlines the step-by-step implementation strategy for the PDF-QA Validation Portal, based on the approved design document.

The goal is to build a high-performance, rich aesthetic web portal for validating PDF-to-HTML parsing. Reviewers can upload PDF and JSON pairs, navigate side-by-side (section-by-section and page-by-page), highlight discrepancies, annotate issues, and track their review progress.

## User Review Required

> [!IMPORTANT]
> The database will be a local SQLite database file, stored under the `backend/data/` directory. All uploads (PDFs and JSONs) will reside in the `backend/uploads/` directory.
> No login or user management is implemented (as per design), but a simple "reviewer name" input/cookie will be used to identify who flagged issues.

## Open Questions

- Should we implement automated mapping suggestion or validation for footnotes (i.e. cross-referencing text markers in the HTML directly with the footnotes array on load, highlighting sections where footnotes exist but no marker is present in the HTML)?
- Are there any specific PDF formatting constraints (like high-DPI scans vs vector text PDFs) we should optimize pdf.js rendering for?

---

## Proposed Changes

### [Backend Component]

We will build a lightweight FastAPI server that acts as a REST API and static file host.

#### [NEW] [main.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/main.py)
Entry point of the FastAPI application. Sets up CORS middleware, includes the routes, and configures static file serving for the `/uploads` directory.

#### [NEW] [database.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/database.py)
Handles SQLite database connection, table initialization (documents, sections, footnotes, annotations), and creates the FTS5 virtual table for full-text search.

#### [NEW] [models.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/models.py)
Pydantic schemas for request validation and response models (Document, Section, Footnote, Annotation, Search results, etc.).

#### [NEW] [json_parser.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/services/json_parser.py)
Service to parse the uploaded enriched JSON, extract chapters, parts, divisions, and sections, and flatten them into database-ready rows.

#### [NEW] [pdf_service.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/services/pdf_service.py)
Service utilizing `pypdf` (or similar python package) to extract basic metadata from uploaded PDF files (such as page counts) to populate database records.

#### [NEW] [documents.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/documents.py)
API endpoints for uploading a document pair, listing all documents with their progress statistics, retrieving a single document, and deleting a document.

#### [NEW] [sections.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/sections.py)
API endpoints for getting document sections (TOC list), getting a single section (with HTML content), getting sections by page number, and updating section review status.

#### [NEW] [annotations.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/annotations.py)
API endpoints for listing annotations, creating a new inline highlight annotation, updating an annotation, and deleting an annotation.

#### [NEW] [footnotes.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/footnotes.py)
API endpoints for updating footnote review status (`approved`, `has_issues`, `pending`).

#### [NEW] [search.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/search.py)
API endpoint to search the flat list of sections using SQLite FTS5 index.

#### [NEW] [export.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/export.py)
API endpoints to compile and export the document's QA report as a downloadable JSON or CSV file.

#### [NEW] [requirements.txt](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/requirements.txt)
Python package dependencies: `fastapi`, `uvicorn`, `aiosqlite`, `python-multipart`, `pypdf`.

---

### [Frontend Component]

We will build a React Single Page Application (SPA) powered by Vite.

#### [NEW] [package.json](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/package.json)
Frontend configuration containing React, Lucide Icons, Zustand (state management), and development/build scripts.

#### [NEW] [index.html](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/index.html)
Main HTML page containing font preconnect elements (Inter font) and the root container div.

#### [NEW] [vite.config.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/vite.config.js)
Vite configuration containing standard React plugin and configurations.

#### [NEW] [index.css](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/index.css)
Core styles, typography settings, utility classes, and light/dark theme variables.

#### [NEW] [uiStore.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/stores/uiStore.js)
Zustand store tracking UI state such as theme, sidebar open/close, active tab, split ratios, and PDF zoom levels.

#### [NEW] [documentStore.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/stores/documentStore.js)
Zustand store for managing loaded documents, sections, active section details, search status, and backend fetch calls.

#### [NEW] [reviewStore.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/stores/reviewStore.js)
Zustand store tracking annotations, text selections, active PDF page, and view mode (Section vs Page view).

#### [NEW] [UploadPage.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/pages/UploadPage.jsx)
Upload interface with drag-and-drop support for PDF and JSON files, pre-upload validation display, and progress tracking.

#### [NEW] [DashboardPage.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/pages/DashboardPage.jsx)
Landing dashboard with document cards, progress rings, overall stats grid, and export shortcuts.

#### [NEW] [ReviewPage.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/pages/ReviewPage.jsx)
The three-column review layout integrating PDF rendering on the left, parsed HTML on the right, and the TOC navigation sidebar.

#### [NEW] [usePdfRenderer.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/hooks/usePdfRenderer.js)
Custom hook encapsulating `pdf.js` worker setup, page retrieval, scale calculation, and viewport canvas rendering.

#### [NEW] [useTextSelection.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/hooks/useTextSelection.js)
Custom hook to monitor mouse selections in the HTML panel and calculate relative start/end text offsets.

#### [NEW] [AppShell.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/layout/AppShell.jsx)
Page container providing the top navigation bar and collapsible sidebar.

#### [NEW] [SplitPane.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/review/SplitPane.jsx)
Resizable panel wrapper allowing smooth drag resize between the PDF and HTML sections.

#### [NEW] [PdfPanel.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/review/PdfPanel.jsx)
Houses the pdf.js rendering canvas, zoom control buttons, and canvas page-flip actions.

#### [NEW] [HtmlPanel.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/review/HtmlPanel.jsx)
Displays parsing HTML with selection event listeners, highlighting markers, and the footnotes panel.

#### [NEW] [AnnotationPopover.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/annotations/AnnotationPopover.jsx)
Floating widget to submit feedback (issue description, severity, reviewer name) near the highlighted text.

#### [NEW] [FootnotePanel.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/footnotes/FootnotePanel.jsx)
Displays list of section-associated footnotes, allowing reviewer validation.

#### [NEW] [api.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/utils/api.js)
Axios/fetch client wrapper with interceptors and helper methods.

---

## Verification Plan

### Automated Tests
- Backend endpoint unit tests using `pytest` and FastAPI's `TestClient`.
- Frontend component rendering validation.

### Manual Verification
- Upload sample ordinance files: `Income Tax Ordinance, 2001 Amended upto 30-06-2018.pdf` and `ordinance-2018-enriched.json`.
- Test the zoom, page navigation, and view switching.
- Perform annotations on HTML text, delete them, and toggle themes.
- Export results to CSV/JSON and verify document structure.
