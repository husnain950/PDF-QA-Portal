from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from datetime import datetime
import uuid
import aiosqlite

from backend.database import get_db
from backend.models import AnnotationCreate, AnnotationResponse, AnnotationUpdate

router = APIRouter(tags=["annotations"])

@router.get("/sections/{section_id}/annotations", response_model=list[AnnotationResponse])
async def list_annotations(section_id: str, db: aiosqlite.Connection = Depends(get_db)):
    # Check if section exists
    async with db.execute("SELECT 1 FROM sections WHERE id = ?", (section_id,)) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Section not found")

    query = """
        SELECT id, section_id, highlighted_text, start_offset, end_offset, issue_description, severity, created_at, reviewer_name
        FROM annotations
        WHERE section_id = ?
        ORDER BY created_at ASC
    """
    async with db.execute(query, (section_id,)) as cursor:
        rows = await cursor.fetchall()

    return [AnnotationResponse(
        id=r["id"],
        section_id=r["section_id"],
        highlighted_text=r["highlighted_text"],
        start_offset=r["start_offset"],
        end_offset=r["end_offset"],
        issue_description=r["issue_description"],
        severity=r["severity"],
        created_at=r["created_at"],
        reviewer_name=r["reviewer_name"]
    ) for r in rows]

@router.post("/sections/{section_id}/annotations", response_model=AnnotationResponse)
async def create_annotation(
    section_id: str,
    body: AnnotationCreate,
    db: aiosqlite.Connection = Depends(get_db)
):
    # Verify section exists and find its document_id
    async with db.execute("SELECT document_id FROM sections WHERE id = ?", (section_id,)) as cursor:
        row = await cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Section not found")
        
    doc_id = row["document_id"]
    annotation_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    try:
        # Create annotation
        await db.execute(
            """
            INSERT INTO annotations (id, section_id, highlighted_text, start_offset, end_offset, issue_description, severity, created_at, reviewer_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                annotation_id, section_id, body.highlighted_text, body.start_offset, body.end_offset,
                body.issue_description, body.severity, created_at, body.reviewer_name
            )
        )

        # Set section status to "has_issues" automatically
        await db.execute(
            "UPDATE sections SET review_status = 'has_issues' WHERE id = ?",
            (section_id,)
        )

        # Set document status to "in_progress"
        await db.execute(
            "UPDATE documents SET status = 'in_progress' WHERE id = ? AND status != 'in_progress'",
            (doc_id,)
        )

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create annotation: {e}")

    return AnnotationResponse(
        id=annotation_id,
        section_id=section_id,
        highlighted_text=body.highlighted_text,
        start_offset=body.start_offset,
        end_offset=body.end_offset,
        issue_description=body.issue_description,
        severity=body.severity,
        created_at=created_at,
        reviewer_name=body.reviewer_name
    )

@router.patch("/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: str,
    body: AnnotationUpdate,
    db: aiosqlite.Connection = Depends(get_db)
):
    # Find existing annotation
    async with db.execute("SELECT * FROM annotations WHERE id = ?", (annotation_id,)) as cursor:
        existing = await cursor.fetchone()
        
    if not existing:
        raise HTTPException(status_code=404, detail="Annotation not found")

    issue_description = body.issue_description if body.issue_description is not None else existing["issue_description"]
    severity = body.severity if body.severity is not None else existing["severity"]

    try:
        await db.execute(
            "UPDATE annotations SET issue_description = ?, severity = ? WHERE id = ?",
            (issue_description, severity, annotation_id)
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update annotation: {e}")

    return AnnotationResponse(
        id=annotation_id,
        section_id=existing["section_id"],
        highlighted_text=existing["highlighted_text"],
        start_offset=existing["start_offset"],
        end_offset=existing["end_offset"],
        issue_description=issue_description,
        severity=severity,
        created_at=existing["created_at"],
        reviewer_name=existing["reviewer_name"]
    )

@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(annotation_id: str, db: aiosqlite.Connection = Depends(get_db)):
    # Find existing annotation to know section_id and doc_id
    query = """
        SELECT a.section_id, s.document_id 
        FROM annotations a
        JOIN sections s ON s.id = a.section_id
        WHERE a.id = ?
    """
    async with db.execute(query, (annotation_id,)) as cursor:
        r = await cursor.fetchone()
        
    if not r:
        raise HTTPException(status_code=404, detail="Annotation not found")

    section_id, doc_id = r["section_id"], r["document_id"]

    try:
        await db.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
        
        # Check if there are other annotations left for this section
        async with db.execute("SELECT COUNT(*) FROM annotations WHERE section_id = ?", (section_id,)) as cursor:
            count_r = await cursor.fetchone()
            
        remaining_count = count_r[0]
        
        # If no issues left and current status is 'has_issues', update it to 'pending' or keep it?
        # Actually, let's keep it as is or change it back to 'pending' if it was 'has_issues' and has no more annotations.
        if remaining_count == 0:
            # Let's verify if section status is currently 'has_issues'. If so, set to 'pending'.
            await db.execute(
                "UPDATE sections SET review_status = 'pending' WHERE id = ? AND review_status = 'has_issues'",
                (section_id,)
            )

        # Recalculate document status
        query_pending = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN review_status = 'pending' THEN 1 END) as pending
            FROM sections
            WHERE document_id = ?
        """
        async with db.execute(query_pending, (doc_id,)) as cursor:
            status_r = await cursor.fetchone()
            
        total_sections = status_r["total"]
        pending_sections = status_r["pending"]

        if pending_sections == 0:
            doc_status = "completed"
        elif pending_sections == total_sections:
            doc_status = "pending"
        else:
            doc_status = "in_progress"

        await db.execute("UPDATE documents SET status = ? WHERE id = ?", (doc_status, doc_id))
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete annotation: {e}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
