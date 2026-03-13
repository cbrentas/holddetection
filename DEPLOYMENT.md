# Deployment Notes

## System Architecture

The holddetection system is designed as a production-shaped machine learning pipeline running on a VPS environment. The architecture decouples the API from the heavy inference processing:

```
Browser
   ↓
Nginx (reverse proxy, handles public traffic)
   ↓
FastAPI API (uvicorn, handles uploads and job creation)
   ↓
PostgreSQL Database + Local Storage
   ↓
Worker Process (background ML inference processor)
```

## Running Services

The system is split into two background systemd services.

### Holddetection API
- **Host:** `127.0.0.1` (localhost only)
- **Port:** `8010`
- **Role:** Exposes endpoints to create jobs, upload images, and retrieve inference results. Nginx will proxy public traffic to this localhost port.

### Holddetection Worker
- **Role:** Continuously polls the database for pending jobs and runs the YOLO object detection inference in the background.

## Service Management

You can manage both the API and the worker using standard systemctl commands. 

*Note: You must first install and enable the generated `.service` files located in the project root.*

### Start Services

```bash
sudo systemctl start holddetection-api
sudo systemctl start holddetection-worker
```

### Stop Services

```bash
sudo systemctl stop holddetection-api
sudo systemctl stop holddetection-worker
```

### Restart Services

```bash
sudo systemctl restart holddetection-api
sudo systemctl restart holddetection-worker
```

### View Logs

To view the live logs of either service, you can tail the systemd journal:

```bash
journalctl -u holddetection-api -f
journalctl -u holddetection-worker -f
```

## Nginx Configuration (Future)

Nginx should be configured to proxy external traffic to the API service running on `localhost:8010`. The FastAPI backend will not be exposed directly to the outside world.
