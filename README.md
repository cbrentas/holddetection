# Hold Detection – Production-Oriented ML Pipeline

## Project Overview

This project is a machine learning backend for climbing wall hold detection. The goal is to detect and locate climbing holds on a wall from an uploaded image using a trained object detection model. It demonstrates a scalable approach transitioning from a notebook-trained model to a production system.

## System Architecture

The architecture relies on an asynchronous job processing pipeline to keep the API responsive while handling heavy object detection tasks.

The pipeline flows as follows:

```
image upload
   ↓
job creation
   ↓
worker processing
   ↓
YOLO inference
   ↓
predictions stored
   ↓
annotated image generated
   ↓
wall and holds projected
   ↓
persistent wall API exposed
   ↓
interactive wall editor UI
```

## Components

The system is composed of several distinct and loosely coupled components:

- **FastAPI backend**: API gateway serving routes and managing the UI.
- **Wall API**: Read-only and editor REST endpoints exposing generated walls and wall holds.
- **Wall Editor UI**: A lightweight, vanilla JS frontend for interactively modifying, hiding, or manually adding bounding boxes on dense spray walls.
- **Async inference worker**: Continuous background process running ML models.
- **PostgreSQL database**: Stores metadata for models, datasets, jobs, walls, and predictions.
- **Storage abstraction**: Encapsulates file operations to allow easy switching of backend storage layers.
- **ML experiment tracking**: Script-based tooling to track training metadata and versions.
- **Dashboard**: Minimal UI for viewing system health, jobs, and experiments.
- **nginx reverse proxy (external)**: Manages incoming production traffic.

## Repository Structure

Key directories and their purpose:

- `app/` - Main application package holding business logic.
- `app/api/` - FastAPI routing and endpoints.
- `app/core/` - Application settings, security, and the storage abstraction layer.
- `app/workers/` - Background worker scripts (e.g., `inference_worker.py`).
- `storage/` - Local filesystem volume for uploads, results, and models.
- `scripts/` - Administrative and tooling scripts (e.g., ML registration).
- `alembic/` - Database migration definitions and env.

## Running Locally

To run the full stack locally for development or testing:

1. **Create virtual environment**: Ensure an isolated Python ecosystem.
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run uvicorn**: Start the FastAPI development server.
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
   ```

4. **Run worker**: Open a second terminal (activate the `venv`) and start the background processor.
   ```bash
   python -m app.workers.inference_worker
   ```

## Environment Variables

Configuration is managed via environment variables. Ensure you create a `.env` file in the root directory. **Do not expose secrets or commit them to the repository.**

A safe `.env.example`:

```
# .env.example
APP_ENV=dev
DATABASE_URL=postgresql://user:password@localhost/dbname
ACTIVE_MODEL_ID=00000000-0000-0000-0000-000000000000
API_USER=admin
API_PASSWORD=secret
```

## Storage

Currently, files (uploaded images, annotated results, and model weights) are stored locally in the `storage/` directory. However, the system utilizes a **Storage Abstraction Layer** making the architecture ready to support S3-compatible storage or object storage backends in the future without changing the core logic.

## ML Experiment Tracking

The repository provides simple tooling to track external ML experiments (e.g., runs from Google Colab) bridging tracking into the application's PostgreSQL database.

You can register runs via scripts:
```bash
python scripts/register_dataset.py dataset.json
python scripts/register_training_run.py training_run.json
```

These scripts insert datasets, training hyperparameters, metrics, artifacts, and optionally linked deployable models.

## Deployment

In production, the system runs on a VPS behind an nginx reverse proxy and operates via `systemd` services (`holddetection-api.service` and `holddetection-worker.service`) ensuring high availability and crash restarts.

## Future Roadmap

Planned additions include:

- **Dataset generation**: Pipelines to build new datasets from edited annotations.
- **Automated training pipeline**: Triggering finetuning directly from the backend.
- **Route creation tools**: Group holds into documented climbing boulders.
- **Mobile application**: Fast and easy route building via mobile snapshots.
