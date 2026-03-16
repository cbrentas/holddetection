import sys
import os
from pathlib import Path

# Add the project root to the python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.db.session import SessionLocal
from app.db.models import Job, JobStatus, Wall, WallHold
from app.services.wall import create_wall_from_job

def run():
    db = SessionLocal()
    try:
        # Find the latest succeeded job
        job = db.query(Job).filter(Job.status == JobStatus.succeeded).order_by(Job.created_at.desc()).first()
        if not job:
            print("No succeeded jobs found.")
            return

        print(f"Testing with Job {job.id} (Upload {job.upload_id})")
        print(f"Job has {len(job.predictions)} predictions.")

        # Delete any existing wall for this upload for a clean test
        existing_wall = db.query(Wall).filter(Wall.original_upload_id == job.upload_id).first()
        if existing_wall:
            print(f"Cleaning up existing wall {existing_wall.id}...")
            db.query(WallHold).filter(WallHold.wall_id == existing_wall.id).delete()
            db.delete(existing_wall)
            db.commit()

        # Pass 1: Create wall
        print("\nPass 1: Creating wall...")
        wall1 = create_wall_from_job(db, job)
        hold_count1 = db.query(WallHold).filter(WallHold.wall_id == wall1.id).count()
        print(f"Wall created: {wall1.id}")
        print(f"Wall holds projected: {hold_count1}")
        
        if hold_count1 != len(job.predictions):
            print(f"ERROR: Expected {len(job.predictions)} holds, got {hold_count1}")

        # Pass 2: Create wall again (should be idempotent)
        print("\nPass 2: Creating wall again with same job...")
        wall2 = create_wall_from_job(db, job)
        hold_count2 = db.query(WallHold).filter(WallHold.wall_id == wall2.id).count()
        
        print(f"Wall created/updated: {wall2.id}")
        print(f"Wall holds total: {hold_count2}")

        if wall1.id != wall2.id:
            print(f"ERROR: Wall ID changed. Expected {wall1.id}, got {wall2.id}")
        
        if hold_count1 != hold_count2:
            print(f"ERROR: Idempotency failed. Hold count changed from {hold_count1} to {hold_count2}")
        else:
            print("SUCCESS: Idempotency verified. No additional holds were created.")

    finally:
        db.close()

if __name__ == "__main__":
    run()
