from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from backend.database import get_db
from backend.models import FootnoteStatusUpdate

router = APIRouter(prefix="/footnotes", tags=["footnotes"])

@router.patch("/{footnote_id}/status")
async def update_footnote_status(
    footnote_id: str,
    body: FootnoteStatusUpdate,
    db: aiosqlite.Connection = Depends(get_db)
):
    # Verify footnote exists
    query = """
        SELECT f.section_id, s.document_id 
        FROM footnotes f
        JOIN sections s ON s.id = f.section_id
        WHERE f.id = ?
    """
    async with db.execute(query, (footnote_id,)) as cursor:
        r = await cursor.fetchone()
        
    if not r:
        raise HTTPException(status_code=404, detail="Footnote not found")

    section_id, doc_id = r["section_id"], r["document_id"]

    try:
        # Update footnote status
        await db.execute(
            "UPDATE footnotes SET review_status = ? WHERE id = ?",
            (body.review_status, footnote_id)
        )

        # Side effect: if footnote has issues, set section status to "has_issues"
        if body.review_status == "has_issues":
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
        raise HTTPException(status_code=500, detail=f"Failed to update footnote status: {e}")

    return {"footnote_id": footnote_id, "review_status": body.review_status}
