import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Job, JobStatus, Prediction
from app.services.inference import run_inference
from app.core.settings import settings
from app.core.storage import make_local_uri, resolve_storage_uri
from pathlib import Path
import cv2

POLL_INTERVAL = 2


def process_job(db: Session, job: Job):
    try:
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        job.attempts += 1
        db.commit()

        image_path = resolve_storage_uri(job.upload.original_uri)
        model_path = resolve_storage_uri(job.model.weights_uri)

        # ---- Run inference ----
        boxes, confs, annotated_image, elapsed = run_inference(
            model_path,
            image_path
        )

        # ---- Save predictions ----
        for (x1, y1, x2, y2), conf in zip(boxes, confs):
            pred = Prediction(
                job_id=job.id,
                class_name="hold",
                confidence=conf,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )
            db.add(pred)

        # ---- Save annotated image ----
        Path(settings.STORAGE_RESULT_DIR).mkdir(parents=True, exist_ok=True)
        result_path = Path(settings.STORAGE_RESULT_DIR) / f"{job.id}.jpg"

        success = cv2.imwrite(str(result_path), annotated_image)
        if not success:
            raise RuntimeError(f"Failed to write annotated image to {result_path}")

        job.result_annotated_uri = make_local_uri(str(result_path))
        
        height, width = 0, 0
        if annotated_image is not None:
            height, width = annotated_image.shape[:2]

        job.inference_meta = {
            "num_predictions": len(boxes),
            "runtime_seconds": elapsed,
            "model_id": str(job.model.id),
            "image_width": width,
            "image_height": height
        }

        job.status = JobStatus.succeeded
        job.finished_at = datetime.utcnow()

        db.commit()

    except Exception as e:
        job.status = JobStatus.failed
        job.error = str(e)
        job.finished_at = datetime.utcnow()
        db.commit()


def run():
    while True:
        db = SessionLocal()

        job = (
            db.query(Job)
            .filter(Job.status == JobStatus.pending)
            .order_by(Job.created_at.asc())
            .first()
        )

        if job:
            process_job(db, job)
        else:
            time.sleep(POLL_INTERVAL)

        db.close()


if __name__ == "__main__":
    run()