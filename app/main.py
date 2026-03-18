from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from app.db.session import get_db
from app.db.models import Upload, Job, JobStatus
from app.core.settings import settings
from app.core.security import basic_auth
from app.core.storage.service import storage

from fastapi.responses import FileResponse, RedirectResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
import os

from fastapi import APIRouter

from app.schemas import WallUpdate, WallHoldCreate, WallHoldUpdate

app = FastAPI(title="Hold Detection API")
api_router = APIRouter(prefix="/bbro/api")

# Mount frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_index():
    return RedirectResponse(url="/bbro/")


@app.get("/bbro", include_in_schema=False)
def redirect_bbro():
    return RedirectResponse(url="/bbro/", status_code=307)


@app.get("/bbro/", include_in_schema=False)
def read_bbro():
    return FileResponse("app/static/index.html")


@app.get("/bbro/dashboard", include_in_schema=False)
def read_dashboard():
    return FileResponse("app/static/dashboard.html")

@api_router.post("/uploads")
def create_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(basic_auth)
):
    upload_id = uuid.uuid4()
    
    saved_uri = storage.save_uploaded_image(str(upload_id), file.file)

    upload = Upload(
        id=upload_id,
        original_uri=saved_uri
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

@api_router.get("/jobs/{job_id}")
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

@api_router.get("/jobs/{job_id}/predictions")
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



@api_router.get("/jobs/{job_id}/image")
def get_result_image(job_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if not job.result_annotated_uri:
        raise HTTPException(status_code=404, detail="Image not ready or not available")

    local_path = storage.resolve_uri(job.result_annotated_uri)
    if not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(local_path)

from sqlalchemy import desc
from app.db.models import Model, TrainingRun, Job, Wall, WallHold

@api_router.get("/dashboard/stats")
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

@api_router.get("/walls")
def get_walls(db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    walls = db.query(Wall).order_by(desc(Wall.created_at)).limit(50).all()
    return [
        {
            "id": str(w.id),
            "title": w.title,
            "status": w.status,
            "original_image_uri": w.original_image_uri,
            "preview_image_uri": w.preview_image_uri,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "updated_at": w.updated_at.isoformat() if w.updated_at else None,
        }
        for w in walls
    ]

@api_router.get("/walls/{wall_id}")
def get_wall(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")
        
    return {
        "id": str(wall.id),
        "title": wall.title,
        "status": wall.status,
        "original_upload_id": str(wall.original_upload_id) if wall.original_upload_id else None,
        "latest_job_id": str(wall.latest_job_id) if wall.latest_job_id else None,
        "original_image_uri": wall.original_image_uri,
        "preview_image_uri": wall.preview_image_uri,
        "created_by": wall.created_by,
        "created_at": wall.created_at.isoformat() if wall.created_at else None,
        "updated_at": wall.updated_at.isoformat() if wall.updated_at else None,
        "meta": wall.meta
    }

@api_router.get("/walls/{wall_id}/holds")
def get_wall_holds(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")
        
    holds = db.query(WallHold).filter(WallHold.wall_id == wall_id).order_by(WallHold.id).all()
    
    return [
        {
            "id": str(h.id),
            "source_type": h.source_type,
            "class_name": h.class_name,
            "confidence": h.confidence,
            "x1": h.x1,
            "y1": h.y1,
            "x2": h.x2,
            "y2": h.y2,
            "center_x": h.center_x,
            "center_y": h.center_y,
            "geometry": h.geometry,
            "label_text": h.label_text,
            "label_x": h.label_x,
            "label_y": h.label_y,
            "is_hidden": h.is_hidden,
            "is_user_adjusted": h.is_user_adjusted,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in holds
    ]

@api_router.get("/jobs/{job_id}/wall")
def get_job_wall(job_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    wall = db.query(Wall).filter(Wall.latest_job_id == job_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found for this job")
        
    return {
        "id": str(wall.id),
        "title": wall.title,
        "status": wall.status,
        "preview_image_uri": wall.preview_image_uri,
        "original_image_uri": wall.original_image_uri,
    }

@api_router.get("/walls/{wall_id}/image")
def get_wall_image(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")
        
    local_path = storage.resolve_uri(wall.original_image_uri)
    if not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="Original image missing on disk")

    return FileResponse(local_path)

@api_router.get("/walls/{wall_id}/preview")
def get_wall_preview(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")
        
    if not wall.preview_image_uri:
        raise HTTPException(status_code=404, detail="Preview image not available")

    local_path = storage.resolve_uri(wall.preview_image_uri)
    if not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="Preview image missing on disk")

    return FileResponse(local_path)

@api_router.patch("/walls/{wall_id}")
def update_wall(wall_id: str, data: WallUpdate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    if data.title is not None:
        wall.title = data.title
    if data.meta is not None:
        wall.meta = data.meta

    db.commit()
    db.refresh(wall)
    return {"status": "success", "id": str(wall.id)}

@api_router.post("/walls/{wall_id}/holds")
def create_wall_hold(wall_id: str, data: WallHoldCreate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    center_x = (data.x1 + data.x2) / 2.0
    center_y = (data.y1 + data.y2) / 2.0

    hold = WallHold(
        wall_id=wall.id,
        prediction_id=None,
        source_type="manual",
        class_name=data.class_name,
        confidence=None,
        x1=data.x1,
        y1=data.y1,
        x2=data.x2,
        y2=data.y2,
        center_x=center_x,
        center_y=center_y,
        geometry=data.geometry,
        label_text=data.label_text,
        label_x=data.label_x,
        label_y=data.label_y,
        is_hidden=data.is_hidden,
        is_user_adjusted=True
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    
    return {"status": "success", "id": str(hold.id)}

@api_router.patch("/walls/{wall_id}/holds/{hold_id}")
def update_wall_hold(wall_id: str, hold_id: str, data: WallHoldUpdate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    hold = db.query(WallHold).filter(WallHold.id == hold_id, WallHold.wall_id == wall_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hold, key, value)

    # Recompute centers if bbox changed
    if any(k in update_data for k in ('x1', 'y1', 'x2', 'y2')):
        if hold.x1 >= hold.x2:
            raise HTTPException(status_code=400, detail="x2 must be strictly greater than x1")
        if hold.y1 >= hold.y2:
            raise HTTPException(status_code=400, detail="y2 must be strictly greater than y1")

        hold.center_x = (hold.x1 + hold.x2) / 2.0
        hold.center_y = (hold.y1 + hold.y2) / 2.0

    hold.is_user_adjusted = True
    db.commit()
    db.refresh(hold)
    
    return {"status": "success", "id": str(hold.id)}

@api_router.delete("/walls/{wall_id}/holds/{hold_id}")
def delete_wall_hold(wall_id: str, hold_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    hold = db.query(WallHold).filter(WallHold.id == hold_id, WallHold.wall_id == wall_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    if hold.source_type != "manual":
        raise HTTPException(status_code=400, detail="Model-derived holds cannot be deleted. Use is_hidden instead.")

    db.delete(hold)
    db.commit()
    return {"status": "success"}

app.include_router(api_router)