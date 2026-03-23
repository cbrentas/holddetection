import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.main import app
from app.core.settings import settings

client = TestClient(app)
auth = (settings.API_USER, settings.API_PASSWORD)

def run():
    print("Testing Route API Endpoints...")

    # 1. Get a Wall ID
    print("\n[ GET /bbro/api/walls ]")
    resp = client.get("/bbro/api/walls", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Expected 200, got {resp.status_code}")
        print(resp.text)
        return
        
    walls = resp.json()
    if not walls:
        print("No walls found. Please create one first.")
        return
        
    wall_id = walls[0]['id']
    print(f"Using Wall {wall_id} for route tests.")

    # 2. Get Wall Holds (we need one for RouteHolds)
    resp = client.get(f"/bbro/api/walls/{wall_id}/holds", auth=auth)
    holds = resp.json()
    if not holds:
         print("No holds found on this wall. RouteHold tests will fail.")
         return
    
    # Let's find a visible hold, and maybe a hidden one if we want to test that
    visible_hold_id = None
    for h in holds:
        if not h.get('is_hidden'):
            visible_hold_id = h['id']
            break
            
    if not visible_hold_id:
        print("No visible hold found, testing might be constrained.")
        return

    # 3. Create a Route
    print(f"\n[ POST /bbro/api/walls/{wall_id}/routes ]")
    route_payload = {
        "name": "Test Route 1",
        "difficulty": "V3",
        "description": "A fun test route",
        "created_by": "TestUser"
    }
    resp = client.post(f"/bbro/api/walls/{wall_id}/routes", json=route_payload, auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Create route failed, got {resp.status_code}")
        print(resp.text)
        return
        
    created_route = resp.json()
    route_id = created_route['id']
    print(f"Success. Route created: {route_id}")

    # 4. List routes
    print(f"\n[ GET /bbro/api/walls/{wall_id}/routes ]")
    resp = client.get(f"/bbro/api/walls/{wall_id}/routes", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: List routes failed, got {resp.status_code}")
    else:
        routes_list = resp.json()
        print(f"Success. Found {len(routes_list)} routes.")
        if created_route['name'] not in [r['name'] for r in routes_list]:
            print("ERROR: Created route not in list.")

    # 5. Get route detail
    print(f"\n[ GET /bbro/api/routes/{route_id} ]")
    resp = client.get(f"/bbro/api/routes/{route_id}", auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Get route failed, got {resp.status_code}")
    else:
        detail = resp.json()
        print(f"Success. Route detail retrieved. holds_count={detail['hold_count']}")
        assert "holds" in detail, "Detail should contain holds array"
    
    # 6. Update Route
    print(f"\n[ PATCH /bbro/api/routes/{route_id} ]")
    resp = client.patch(f"/bbro/api/routes/{route_id}", json={"difficulty": "V4"}, auth=auth)
    if resp.status_code != 200:
         print(f"ERROR: Update route failed, got {resp.status_code}")
    else:
         print("Success. Route difficulty updated.")

    # 7. Add Route Hold
    print(f"\n[ POST /bbro/api/routes/{route_id}/holds ]")
    hold_payload = {
        "wall_hold_id": visible_hold_id,
        "role": "start",
        "order_index": 1
    }
    resp = client.post(f"/bbro/api/routes/{route_id}/holds", json=hold_payload, auth=auth)
    if resp.status_code != 200:
        print(f"ERROR: Add route hold failed, got {resp.status_code}")
        print(resp.text)
        return
        
    route_hold_id = resp.json()['id']
    print(f"Success. Added wall hold {visible_hold_id} to route, route_hold_id: {route_hold_id}")

    # 8. Duplicate Route Hold (Should fail)
    print(f"\n[ POST /bbro/api/routes/{route_id}/holds ] (Duplicate test)")
    resp = client.post(f"/bbro/api/routes/{route_id}/holds", json=hold_payload, auth=auth)
    if resp.status_code == 400:
        print("Success. Duplicate rejected properly.")
    else:
        print(f"ERROR: Expected 400 for duplicate, got {resp.status_code}")

    # 9. Get Route Details (check holds logic)
    print(f"\n[ GET /bbro/api/routes/{route_id} ] (Check holds inside details)")
    resp = client.get(f"/bbro/api/routes/{route_id}", auth=auth)
    if resp.status_code == 200:
         r = resp.json()
         print(f"Success. Route detail hold count is {len(r['holds'])}")
         if len(r['holds']) > 0:
             rh = r['holds'][0]
             print(f"Found hold in array: role={rh['role']}, order_index={rh['order_index']}")
    else:
         print(f"ERROR: failed {resp.status_code}")
         
    # 10. Update Route Hold
    print(f"\n[ PATCH /bbro/api/routes/{route_id}/holds/{route_hold_id} ]")
    resp = client.patch(f"/bbro/api/routes/{route_id}/holds/{route_hold_id}", json={"role": "hand", "order_index": 2}, auth=auth)
    if resp.status_code != 200:
         print(f"ERROR: Update route hold failed, got {resp.status_code}")
    else:
         print("Success. Route hold updated.")

    # 11. Delete Route Hold
    print(f"\n[ DELETE /bbro/api/routes/{route_id}/holds/{route_hold_id} ]")
    resp = client.delete(f"/bbro/api/routes/{route_id}/holds/{route_hold_id}", auth=auth)
    if resp.status_code != 200:
         print(f"ERROR: Delete route hold failed, got {resp.status_code}")
    else:
         print("Success. Route hold deleted.")
         
    # 12. Delete Route
    print(f"\n[ DELETE /bbro/api/routes/{route_id} ]")
    resp = client.delete(f"/bbro/api/routes/{route_id}", auth=auth)
    if resp.status_code != 200:
         print(f"ERROR: Delete route failed, got {resp.status_code}")
    else:
         print("Success. Route deleted.")

    print("\nAll Route API tests completed.")

if __name__ == "__main__":
    run()
