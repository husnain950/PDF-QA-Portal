import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.routes import documents, sections, annotations, footnotes, search, export

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    await init_db()
    yield

app = FastAPI(title="PDF-QA Portal API", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire up routers
app.include_router(documents.router, prefix="/api")
app.include_router(sections.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(footnotes.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(export.router, prefix="/api")

# Mount uploads directory for static PDF serving
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/health")
def health_check():
    return {"status": "ok"}
