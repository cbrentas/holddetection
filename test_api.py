import urllib.request
import json
import base64

auth = b"Basic " + base64.b64encode(b"w0nts4y:v3ryc00l")

req = urllib.request.Request("http://127.0.0.1:8010/bbro/api/walls")
req.add_header("Authorization", auth.decode('utf-8'))

try:
    with urllib.request.urlopen(req) as response:
        walls = json.loads(response.read().decode())
        print(f"FETCHED {len(walls)} WALLS")
        if len(walls) > 0:
            wall_id = walls[0]['id']
            print(f"WALL ID: {wall_id}")
            
            # Fetch /edit
            edit_req = urllib.request.Request(f"http://127.0.0.1:8010/bbro/walls/{wall_id}/edit")
            with urllib.request.urlopen(edit_req) as edit_res:
                print(f"/edit status: {edit_res.status}")
                
            # Fetch /image
            img_req = urllib.request.Request(f"http://127.0.0.1:8010/bbro/api/walls/{wall_id}/image")
            img_req.add_header("Authorization", auth.decode('utf-8'))
            with urllib.request.urlopen(img_req) as img_res:
                print(f"/image status: {img_res.status}")
                
            # Fetch /holds
            holds_req = urllib.request.Request(f"http://127.0.0.1:8010/bbro/api/walls/{wall_id}/holds")
            holds_req.add_header("Authorization", auth.decode('utf-8'))
            with urllib.request.urlopen(holds_req) as holds_res:
                print(f"/holds status: {holds_res.status}")
except Exception as e:
    print(f"ERROR: {e}")

