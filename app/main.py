from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from app.db.session import get_db
from app.db.models import Upload, Job, JobStatus
from app.core.settings import settings
from app.core.security import basic_auth
from app.core.storage import make_local_uri, resolve_storage_uri

from fastapi.responses import FileResponse, RedirectResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Hold Detection API")

# Mount frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_index():
    return RedirectResponse(url="/bbro")

@app.get("/bbro")
def read_bbro():
    return FileResponse("app/static/index.html")

@app.get("/bbro/dashboard")
def read_dashboard():
    return FileResponse("app/static/dashboard.html")

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
        original_uri=make_local_uri(str(file_path))
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
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if not job.result_annotated_uri:
        raise HTTPException(status_code=404, detail="Image not ready or not available")

    local_path = resolve_storage_uri(job.result_annotated_uri)
    if not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(local_path)

from sqlalchemy import desc
from app.db.models import Model, TrainingRun, Job

@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    active_model = None
    if settings.ACTIVE_MODEL_ID:
        try:
            am = db.query(Model).filter(Model.id == settings.ACTIVE_MODEL_ID).first()
            if am:
                active_model = {
                    "id": str(am.id),
                    "name": am.name,
                    "version": am.version,
                    "task": am.task,
                    "created_at": am.created_at.isoformat()
                }
        except Exception:
            pass

    recent_jobs = []
    try:
        jobs = db.query(Job).order_by(desc(Job.created_at)).limit(10).all()
        for j in jobs:
            recent_jobs.append({
                "id": str(j.id),
                "status": j.status,
                "model_id": str(j.model_id),
                "created_at": j.created_at.isoformat(),
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            })
    except Exception:
        pass

    recent_runs = []
    try:
        runs = db.query(TrainingRun).order_by(desc(TrainingRun.created_at)).limit(5).all()
        for r in runs:
            recent_runs.append({
                "id": str(r.id),
                "status": r.status,
                "metrics": r.metrics,
                "hyperparams": r.hyperparams,
                "created_at": r.created_at.isoformat()
            })
    except Exception:
        pass
        
    return {
        "active_model": active_model,
        "recent_jobs": recent_jobs,
        "recent_training_runs": recent_runs
    }