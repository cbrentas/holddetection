from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pathlib import Path
import uuid
from app.db.session import get_db
from app.db.models import Upload, Job, JobStatus, Model, TrainingRun, Wall, WallHold, Route, RouteHold
from app.core.settings import settings
from app.core.security import basic_auth
from app.core.storage.service import storage

from fastapi.responses import FileResponse, RedirectResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles


from fastapi import APIRouter

from app.schemas import WallUpdate, WallHoldCreate, WallHoldUpdate, RouteCreate, RouteUpdate, RouteHoldCreate, RouteHoldUpdate
from app.routers import auth
import json

RUNS_DIR = Path(__file__).resolve().parent / "static" / "runs"

app = FastAPI(title="Hold Detection API")
api_router = APIRouter(prefix="/bbro/api")

# Mount frontend
app.mount("/bbro/static", StaticFiles(directory="app/static"), name="static")

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

@app.get("/bbro/walls/{wall_id}/edit", include_in_schema=False)
def read_editor(wall_id: str):
    return FileResponse("app/static/editor.html")

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
    print(f"DEBUG: resolve_uri('{wall.original_image_uri}') -> {local_path}")
    print(f"DEBUG: Path exists? {Path(local_path).exists()}")
    
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

# --- Routes API ---

@api_router.get("/walls/{wall_id}/routes")
def get_wall_routes(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    routes = db.query(Route).filter(Route.wall_id == wall_id).order_by(desc(Route.updated_at)).all()
    
    return [
        {
            "id": str(r.id),
            "wall_id": str(r.wall_id),
            "name": r.name,
            "difficulty": r.difficulty,
            "description": r.description,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "hold_count": len(r.holds)
        }
        for r in routes
    ]

@api_router.post("/walls/{wall_id}/routes")
def create_wall_route(wall_id: str, data: RouteCreate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    try:
        route = Route(
            wall_id=wall.id,
            name=data.name,
            difficulty=data.difficulty,
            description=data.description,
            created_by=data.created_by
        )
        db.add(route)
        db.commit()
        db.refresh(route)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "id": str(route.id),
        "wall_id": str(route.wall_id),
        "name": route.name,
        "difficulty": route.difficulty,
        "description": route.description,
        "created_by": route.created_by,
        "created_at": route.created_at.isoformat() if route.created_at else None,
        "updated_at": route.updated_at.isoformat() if route.updated_at else None,
        "hold_count": 0
    }

@api_router.get("/routes/{route_id}")
def get_route(route_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Sort route holds exactly as requested
    sorted_holds = sorted(
        route.holds, 
        key=lambda rh: (
            rh.order_index if rh.order_index is not None else float('inf'),
            rh.created_at.timestamp() if rh.created_at else 0
        )
    )

    return {
        "id": str(route.id),
        "wall_id": str(route.wall_id),
        "name": route.name,
        "difficulty": route.difficulty,
        "description": route.description,
        "created_by": route.created_by,
        "created_at": route.created_at.isoformat() if route.created_at else None,
        "updated_at": route.updated_at.isoformat() if route.updated_at else None,
        "hold_count": len(sorted_holds),
        "holds": [
            {
                "route_hold_id": str(rh.id),
                "wall_hold_id": str(rh.wall_hold_id),
                "role": rh.role,
                "order_index": rh.order_index
            }
            for rh in sorted_holds
        ]
    }

@api_router.patch("/routes/{route_id}")
def update_route(route_id: str, data: RouteUpdate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        return {"status": "success", "id": str(route.id)}
        
    try:
        for key, value in update_data.items():
            setattr(route, key, value)
            
        db.commit()
        db.refresh(route)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "id": str(route.id)}

@api_router.delete("/routes/{route_id}")
def delete_route(route_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
        
    try:
        db.delete(route)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success"}

@api_router.get("/routes/{route_id}/holds")
def get_route_holds(route_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    sorted_holds = sorted(
        route.holds, 
        key=lambda rh: (
            rh.order_index if rh.order_index is not None else float('inf'),
            rh.created_at.timestamp() if rh.created_at else 0
        )
    )

    return [
        {
            "route_hold_id": str(rh.id),
            "wall_hold_id": str(rh.wall_hold_id),
            "role": rh.role,
            "order_index": rh.order_index
        }
        for rh in sorted_holds
    ]

@api_router.post("/routes/{route_id}/holds")
def create_route_hold(route_id: str, data: RouteHoldCreate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    wall_hold = db.query(WallHold).filter(WallHold.id == data.wall_hold_id).first()
    if not wall_hold:
        raise HTTPException(status_code=400, detail="Wall hold does not exist")
        
    if str(wall_hold.wall_id) != str(route.wall_id):
        raise HTTPException(status_code=400, detail="Wall hold belongs to a different wall")
        
    if wall_hold.is_hidden:
        raise HTTPException(status_code=400, detail="Cannot add a hidden wall hold to a route")
        
    existing_rh = db.query(RouteHold).filter(RouteHold.route_id == route.id, RouteHold.wall_hold_id == wall_hold.id).first()
    if existing_rh:
        raise HTTPException(status_code=400, detail="Hold is already added to this route")

    try:
        rh = RouteHold(
            route_id=route.id,
            wall_hold_id=wall_hold.id,
            role=data.role,
            order_index=data.order_index
        )
        db.add(rh)
        db.commit()
        db.refresh(rh)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "id": str(rh.id)}

@api_router.patch("/routes/{route_id}/holds/{route_hold_id}")
def update_route_hold(route_id: str, route_hold_id: str, data: RouteHoldUpdate, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    rh = db.query(RouteHold).filter(RouteHold.id == route_hold_id, RouteHold.route_id == route_id).first()
    if not rh:
        raise HTTPException(status_code=404, detail="Route hold not found")

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        return {"status": "success", "id": str(rh.id)}
        
    try:
        for key, value in update_data.items():
            setattr(rh, key, value)
            
        db.commit()
        db.refresh(rh)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "id": str(rh.id)}

@api_router.delete("/routes/{route_id}/holds/{route_hold_id}")
def delete_route_hold(route_id: str, route_hold_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    rh = db.query(RouteHold).filter(RouteHold.id == route_hold_id, RouteHold.route_id == route_id).first()
    if not rh:
        raise HTTPException(status_code=404, detail="Route hold not found")

    try:
        db.delete(rh)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success"}

@api_router.get("/walls/{wall_id}/routes/full")
def get_wall_routes_full(wall_id: str, db: Session = Depends(get_db), username: str = Depends(basic_auth)):
    wall = db.query(Wall).filter(Wall.id == wall_id).first()
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    wall_holds = db.query(WallHold).filter(WallHold.wall_id == wall_id).order_by(WallHold.id).all()
    routes = db.query(Route).filter(Route.wall_id == wall_id).order_by(desc(Route.updated_at)).all()

    routes_arr = []
    for r in routes:
        sorted_holds = sorted(
            r.holds, 
            key=lambda rh: (
                rh.order_index if rh.order_index is not None else float('inf'),
                rh.created_at.timestamp() if rh.created_at else 0
            )
        )
        routes_arr.append({
            "id": str(r.id),
            "wall_id": str(r.wall_id),
            "name": r.name,
            "difficulty": r.difficulty,
            "description": r.description,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "hold_count": len(sorted_holds),
            "holds": [
                {
                    "route_hold_id": str(rh.id),
                    "wall_hold_id": str(rh.wall_hold_id),
                    "role": rh.role,
                    "order_index": rh.order_index
                }
                for rh in sorted_holds
            ]
        })
        
    holds_arr = [
        {
            "id": str(h.id),
            "class_name": h.class_name,
            "x1": h.x1,
            "y1": h.y1,
            "x2": h.x2,
            "y2": h.y2,
            "center_x": h.center_x,
            "center_y": h.center_y,
            "label_text": h.label_text,
            "label_x": h.label_x,
            "label_y": h.label_y,
            "is_hidden": h.is_hidden,
        }
        for h in wall_holds
    ]

    return {
        "wall": {
            "id": str(wall.id),
            "title": wall.title,
            "status": wall.status,
            "original_image_uri": wall.original_image_uri,
            "preview_image_uri": wall.preview_image_uri,
            "created_at": wall.created_at.isoformat() if wall.created_at else None,
            "updated_at": wall.updated_at.isoformat() if wall.updated_at else None,
        },
        "wall_holds": holds_arr,
        "routes": routes_arr
    }

@api_router.get("/training-runs-local")
def get_local_training_runs(username: str = Depends(basic_auth)):
    runs = []

    if not RUNS_DIR.exists():
        return []

    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue

        meta_file = run_dir / "metadata.json"
        if not meta_file.exists():
            continue

        try:
            with open(meta_file) as f:
                meta = json.load(f)

            runs.append({
                "id": run_dir.name,
                "meta": meta,
                "images": {
                    "results": f"/bbro/static/runs/{run_dir.name}/results.png",
                    "confusion": f"/bbro/static/runs/{run_dir.name}/confusion_matrix.png"
                }
            })
        except Exception:
            continue

    # newest first
    runs.sort(key=lambda x: x["meta"].get("run_id", ""), reverse=True)

    return runs

app.include_router(api_router)
app.include_router(auth.router)