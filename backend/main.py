import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend.database import init_db
from backend.routes import documents, sections, annotations, footnotes, search, export

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed data logic if target files/directories are empty
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Database seeding
    db_dir = os.path.join(backend_dir, "data")
    db_path = os.path.join(db_dir, "qa_portal.db")
    seed_db_path = os.path.join(backend_dir, "seed_data", "qa_portal.db")
    
    os.makedirs(db_dir, exist_ok=True)
    if not os.path.exists(db_path) and os.path.exists(seed_db_path):
        print(f"Seeding database from {seed_db_path} to {db_path}...")
        import shutil
        shutil.copy(seed_db_path, db_path)
        
    # 2. Uploads seeding
    upload_dir = os.path.join(backend_dir, "uploads")
    seed_upload_dir = os.path.join(backend_dir, "seed_uploads")
    
    os.makedirs(upload_dir, exist_ok=True)
    current_files = [f for f in os.listdir(upload_dir) if f != ".gitkeep"]
    if len(current_files) == 0 and os.path.exists(seed_upload_dir):
        print(f"Seeding uploads from {seed_upload_dir} to {upload_dir}...")
        import shutil
        for item in os.listdir(seed_upload_dir):
            if item != ".gitkeep":
                src = os.path.join(seed_upload_dir, item)
                dst = os.path.join(upload_dir, item)
                if os.path.isfile(src):
                    shutil.copy(src, dst)

    # Initialize database on startup
    await init_db()
    
    # Force garbage collection to free up memory from startup copies
    import gc
    gc.collect()
    
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
