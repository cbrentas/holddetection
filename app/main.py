from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from app.db.session import get_db
from app.db.models import Upload, Job, JobStatus
from app.core.settings import settings
from app.core.security import basic_auth

from fastapi.responses import FileResponse

app = FastAPI(title="Hold Detection API")

# Ensure directories exist
Path(settings.STORAGE_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

@app.post("/uploads")
def create_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(basic_auth)
):
    upload_id = uuid.uuid4()
    file_path = Path(settings.STORAGE_UPLOAD_DIR) / f"{upload_id}.jpg"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    upload = Upload(
        id=upload_id,
        original_uri=str(file_path)
    )
    db.add(upload)
    db.commit()

    job = Job(
        upload_id=upload.id,
        model_id=settings.ACTIVE_MODEL_ID,
        status=JobStatus.pending
    )
    db.add(job)
    db.commit()

    return {
        "upload_id": str(upload.id),
        "job_id": str(job.id),
        "status": job.status
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {"error": "not found"}

    return {
        "status": job.status,
        "error": job.error,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }

@app.get("/jobs/{job_id}/predictions")
def get_predictions(job_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {"error": "not found"}

    return [
        {
            "confidence": p.confidence,
            "x1": p.x1,
            "y1": p.y1,
            "x2": p.x2,
            "y2": p.y2,
        }
        for p in job.predictions
    ]



@app.get("/jobs/{job_id}/image")
def get_result_image(job_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or not job.result_annotated_uri:
        return {"error": "not ready"}

    return FileResponse(job.result_annotated_uri)