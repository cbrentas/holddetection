# Deployment Notes

## Existing Services on VPS

Current running apps:

- cryptocurr FastAPI app
  - uvicorn
  - port: 127.0.0.1:8000

## Holddetection Service

Holddetection must run on a different port.

Recommended configuration:

uvicorn app.main:app --host 127.0.0.1 --port 8010

Important:
- Must bind only to localhost
- Public traffic must go through nginx

## Nginx

Example nginx config:

server {
    listen 80;
    server_name holddetection.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

## Storage

Current storage backend: local filesystem

storage/
- uploads
- results
- models

Future:
- migrate to S3-compatible object storage