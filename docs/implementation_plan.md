# Implementation Plan — Global Document Issues and Resolution Workflow

This plan details the implementation of a document-wide ("global") issue validation and resolution system.

---

## Proposed Changes

### Database & Backend

We will extend the `annotations` table schema to track an issue's status ('open' or 'resolved') and provide a document-wide retrieval endpoint.

#### [MODIFY] [database.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/database.py)
* Add `status TEXT NOT NULL DEFAULT 'open'` to the `annotations` table creation statement.
* Add an automatic startup migration check that runs `ALTER TABLE annotations ADD COLUMN status TEXT NOT NULL DEFAULT 'open';` if the column doesn't exist.

#### [MODIFY] [models.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/models.py)
* Add `status: str = "open"` to `AnnotationBase` and `AnnotationResponse`.
* Add `status: Optional[str] = None` to `AnnotationUpdate`.

#### [MODIFY] [annotations.py](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/backend/routes/annotations.py)
* **New Route**: Add `GET /documents/{document_id}/annotations` which returns a flat list of all annotations belonging to a document (by joining `annotations` with `sections`).
* **Route Update**: Update `PATCH /annotations/{annotation_id}` to handle the `status` update:
  - If status becomes `resolved`:
    - Check if there are any remaining `open` annotations (section or footnote level) for that section. If no open annotations remain, change the section status from `has_issues` back to `pending`.
  - If status becomes `open` (unresolved):
    - Ensure the parent section status is updated to `has_issues`.

---

### Frontend Zustand Store

We will track all document-level annotations globally in Zustand so that changes in the sidebar sync immediately.

#### [MODIFY] [reviewStore.js](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/stores/reviewStore.js)
* Introduce a state array `globalAnnotations: []`.
* Add `fetchGlobalAnnotations: async (documentId)` to query the new backend endpoint.
* Add `toggleAnnotationStatus: async (annotationId, currentStatus)` to toggle between `'open'` and `'resolved'`, updating the local active `annotations` state, `globalAnnotations` state, and the section review status.
* Update `createAnnotation` and `deleteAnnotation` to append/remove annotations from `globalAnnotations` dynamically.

---

### UI Panels

We will create a clean "Open vs. Resolved" interface tab in the sidebar.

#### [MODIFY] [Sidebar.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/layout/Sidebar.jsx)
* Automatically trigger `fetchGlobalAnnotations` on load.
* Modify the "Issues" tab name to show the count of **open** issues across the entire document.
* Add a sub-tab bar inside the Issues tab: **Open ({openCount})** and **Resolved ({resolvedCount})**.
* Display global issue cards. Each card will show:
  - The section header/footnote marker it belongs to (e.g. "Section 4" or "Section 4 · Footnote 1").
  - The highlighted mismatch text and its description.
  - A checkbox/tick action to resolve/unresolve the issue.
  - An onClick action to transition the workspace directly to the target section.

#### [MODIFY] [HtmlPanel.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/review/HtmlPanel.jsx)
* Skip drawing highlights for resolved annotations (`if (annot.status === 'resolved') return`).

#### [MODIFY] [FootnotePanel.jsx](file:///Users/muhammad.husnain/Downloads/code/AG/PDF-QA-Portal/frontend/src/components/footnotes/FootnotePanel.jsx)
* Skip drawing highlights inside footnote texts for resolved annotations.

---

## Verification Plan

### Automated Checks
* Verify backend builds and runs successfully.
* Verify SQLite database schema updates automatically on startup.

### Manual Verification
1. Open the web portal.
2. Select text in a section, save it as an issue, and verify it appears in the **Global Issues -> Open** tab in the sidebar.
3. Toggle the checkmark next to the issue. Verify it immediately transitions to the **Resolved** tab.
4. Verify the yellow text highlight in the HTML pane vanishes when the issue is marked resolved, and reappears if marked unresolved.
5. Verify clicking the issue card in the sidebar automatically jumps the PDF and HTML panel view to that specific section.
