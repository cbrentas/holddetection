from sqlalchemy.orm import Session
from app.db.models import Job, Wall, WallHold, Prediction

def create_wall_from_job(db: Session, job: Job) -> Wall:
    """
    Creates a Wall and projects Predictions into WallHolds.
    
    Design note (for future editor):
    Annotated YOLO images are preview artifacts only.
    The editor and interactive overlays must always use the original upload image
    and render wall_holds dynamically.
    """
    
    # 1. Find an existing Wall for the job.upload_id or create a new one.
    wall = db.query(Wall).filter(Wall.original_upload_id == job.upload_id).first()
    if not wall:
        wall = Wall(
            title=f"Wall {job.upload.id}",
            original_upload_id=job.upload_id,
            original_image_uri=job.upload.original_uri,
        )
        if job.result_annotated_uri:
            wall.preview_image_uri = job.result_annotated_uri
        db.add(wall)
        db.flush() # flush to get wall.id
        
    # 2-5. Update wall metadata
    wall.latest_job_id = job.id
    wall.original_image_uri = job.upload.original_uri
    if job.result_annotated_uri:
        wall.preview_image_uri = job.result_annotated_uri
    wall.status = "ready"
    
    # 6. Implement idempotency: query existing WallHold.prediction_ids linked to the wall.
    existing_prediction_ids = {
        wh.prediction_id 
        for wh in db.query(WallHold.prediction_id).filter(WallHold.wall_id == wall.id).all()
        if wh.prediction_id is not None
    }
    
    # 7-8. Project predictions into WallHolds
    for prediction in job.predictions:
        if prediction.id in existing_prediction_ids:
            continue
            
        center_x = (prediction.x1 + prediction.x2) / 2
        center_y = (prediction.y1 + prediction.y2) / 2
        
        wall_hold = WallHold(
            wall_id=wall.id,
            prediction_id=prediction.id,
            source_type="model",
            class_name=prediction.class_name,
            confidence=prediction.confidence,
            x1=prediction.x1,
            y1=prediction.y1,
            x2=prediction.x2,
            y2=prediction.y2,
            center_x=center_x,
            center_y=center_y,
            label_text=prediction.class_name, # Default to class name
            is_hidden=False,
            is_user_adjusted=False
        )
        db.add(wall_hold)
        
    db.commit()
    return wall
