import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.main import app

client = TestClient(app)

# Note: The endpoints use Depends(basic_auth)
# Basic auth credentials configured in settings
from app.core.settings import settings

auth = (settings.API_USER, settings.API_PASSWORD)

def run():
    print("Testing Wall API Endpoints...")

    # 1. List Walls
    print("\n[ GET /bbro/api/walls ]")
    resp = client.get("/bbro/api/walls", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Expected 200, got {resp.status_code}")
        print(resp.text)
        return
        
    walls = resp.json()
    print(f"Success. Retrieved {len(walls)} walls.")
    
    if not walls:
        print("No walls found to run detailed tests on. Please upload an image and wait for a job to complete.")
        return
        
    # Get the most recent wall
    test_wall = walls[0]
    wall_id = test_wall['id']
    print(f"\nUsing Wall {wall_id} for detailed tests.")

    # 2. Get Wall details
    print(f"\n[ GET /bbro/api/walls/{wall_id} ]")
    resp = client.get(f"/bbro/api/walls/{wall_id}", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Expected 200, got {resp.status_code}")
        print(resp.text)
        return
        
    wall_details = resp.json()
    print("Success. Retrieved wall details.")
    # Check expected keys
    expected_keys = ['id', 'title', 'status', 'original_upload_id', 'latest_job_id', 'original_image_uri', 'preview_image_uri', 'created_by', 'created_at', 'updated_at', 'meta']
    missing_keys = [k for k in expected_keys if k not in wall_details]
    if missing_keys:
        print(f"ERROR: Missing expected keys in wall details: {missing_keys}")
    else:
        print("Schema validation passed.")
        
    latest_job_id = wall_details.get('latest_job_id')

    # 3. Get Wall Holds
    print(f"\n[ GET /bbro/api/walls/{wall_id}/holds ]")
    resp = client.get(f"/bbro/api/walls/{wall_id}/holds", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Expected 200, got {resp.status_code}")
        print(resp.text)
        return
        
    holds = resp.json()
    print(f"Success. Retrieved {len(holds)} holds.")
    if len(holds) > 0:
        expected_hold_keys = ['id', 'source_type', 'class_name', 'confidence', 'x1', 'y1', 'x2', 'y2', 'center_x', 'center_y', 'geometry', 'label_text', 'label_x', 'label_y', 'is_hidden', 'is_user_adjusted', 'created_at']
        missing_keys = [k for k in expected_hold_keys if k not in holds[0]]
        if missing_keys:
             print(f"ERROR: Missing expected keys in wall hold details: {missing_keys}")
        else:
             print("Hold schema validation passed.")

    # 4. Get Job Wall
    if latest_job_id:
        print(f"\n[ GET /bbro/api/jobs/{latest_job_id}/wall ]")
        resp = client.get(f"/bbro/api/jobs/{latest_job_id}/wall", auth=auth)
        if resp.status_code != 200:
            print(f"ERROR: Expected 200, got {resp.status_code}")
            print(resp.text)
            return
            
        job_wall = resp.json()
        print("Success. Retrieved wall for job.")
        if job_wall['id'] != wall_id:
            print(f"ERROR: Job wall id mismatch. Expected {wall_id}, got {job_wall['id']}")
    else:
        print("\nSkipping GET /bbro/api/jobs/{job_id}/wall as wall has no latest_job_id")
        
    print("\nAll API tests completed.")

if __name__ == "__main__":
    run()
