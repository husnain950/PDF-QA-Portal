from pydantic import BaseModel, Field
from typing import List, Optional

# --- Document Models ---

class DocumentStats(BaseModel):
    reviewed: int
    approved: int
    has_issues: int
    pending: int

class DocumentBase(BaseModel):
    name: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: str
    pdf_filename: str
    json_filename: str
    total_sections: int
    total_pages: int
    uploaded_at: str
    status: str
    stats: Optional[DocumentStats] = None

    class Config:
        from_attributes = True

# --- Annotation Models ---

class AnnotationBase(BaseModel):
    highlighted_text: str
    start_offset: int
    end_offset: int
    issue_description: Optional[str] = None
    severity: str = "error" # "error" | "warning" | "info"
    reviewer_name: Optional[str] = None

class AnnotationCreate(AnnotationBase):
    pass

class AnnotationUpdate(BaseModel):
    issue_description: Optional[str] = None
    severity: Optional[str] = None

class AnnotationResponse(AnnotationBase):
    id: str
    section_id: str
    created_at: str

    class Config:
        from_attributes = True

# --- Footnote Models ---

class FootnoteBase(BaseModel):
    marker: str
    page: Optional[int] = None
    text: str

class FootnoteResponse(FootnoteBase):
    id: str
    section_id: str
    review_status: str

    class Config:
        from_attributes = True

class FootnoteStatusUpdate(BaseModel):
    review_status: str # "approved" | "has_issues" | "pending"

# --- Section Models ---

class SectionMetadataResponse(BaseModel):
    id: str
    document_id: str
    chapter_code: Optional[str] = None
    chapter_heading: Optional[str] = None
    part_code: Optional[str] = None
    part_heading: Optional[str] = None
    division_code: Optional[str] = None
    division_heading: Optional[str] = None
    section_code: str
    section_heading: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    review_status: str
    annotation_count: int
    sort_order: int

    class Config:
        from_attributes = True

class SectionResponse(SectionMetadataResponse):
    html_content: Optional[str] = None
    plain_text: Optional[str] = None
    footnotes: List[FootnoteResponse] = []

    class Config:
        from_attributes = True

class SectionStatusUpdate(BaseModel):
    review_status: str # "approved" | "has_issues" | "pending"

# --- Search Models ---

class SearchResultResponse(BaseModel):
    section_id: str
    section_code: str
    section_heading: str
    chapter_code: Optional[str] = None
    snippet: str
    match_count: int

# --- Export Models ---

class ExportSummary(BaseModel):
    total_annotations: int
    by_severity: dict
    completion_percentage: float
    generated_at: str

class SectionExport(BaseModel):
    code: str
    heading: str
    chapter: str
    pages: str
    review_status: str
    annotations: List[AnnotationBase]

class FootnoteExport(BaseModel):
    section_code: str
    marker: str
    text: str
    review_status: str

class DocumentExport(BaseModel):
    name: str
    uploaded_at: str
    total_sections: int
    reviewed: int
    approved: int
    has_issues: int

class ExportResponse(BaseModel):
    document: DocumentExport
    sections: List[SectionExport]
    footnotes: List[FootnoteExport]
    summary: ExportSummary
