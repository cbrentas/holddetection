# Hold Detection – Production-Oriented ML Pipeline

A production-shaped object detection pipeline for climbing wall hold detection.

This project demonstrates how to move from a notebook-trained YOLO model to a scalable backend system with:

- Asynchronous job processing
- Model versioning
- Training metadata tracking
- Database-backed inference pipeline
- Clean separation between API and worker
- Future-ready architecture for scaling and GPU deployment

---

## Overview

The system is deployed on a VPS and will be exposed publicly using Nginx as a reverse proxy.

Architecture:

Client (HTML / App)
↓
FastAPI API (authentication + upload handling)
↓
PostgreSQL (jobs + metadata)
↓
Worker Process (async inference)
↓
Predictions + Annotated Image Storage

---

## Core Features

### 1. Asynchronous Inference

Uploads create a `Job` record in PostgreSQL.

A background worker:

- Polls pending jobs
- Loads the active model
- Runs inference
- Stores predictions in the database
- Saves annotated result image
- Updates job status

This design allows:

- Horizontal scaling (multiple workers)
- Future GPU migration without API changes
- Retry logic
- Failure isolation

---

### 2. Model Versioning

The system stores models in a `models` table:

- name
- version
- weights URI
- training run reference
- metadata

The active model is controlled via environment variable:

```
ACTIVE_MODEL_ID=<uuid>
```

This allows:

- Re-running inference with new models
- Tracking model evolution
- Safe production upgrades

---

### 3. Training Run Tracking

Schema supports:

- datasets
- training_runs
- artifacts (weights, plots, metrics)
- reproducibility metadata

Training is currently done externally (Google Colab GPU),
and artifacts are registered in the database after export.

Colab is NOT part of the production inference pipeline.

---

### 4. Database Schema (High-Level)

Core Tables:

- datasets
- training_runs
- artifacts
- models
- uploads
- jobs
- predictions

The schema supports:

- Future segmentation support
- Reprocessing historical uploads
- Route-building features
- Model performance tracking

---

## Project Structure

```
holddetection/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── services/
│   └── workers/
│
├── alembic/
├── storage/
├── requirements.txt
└── README.md
```

Separation of concerns:

- API layer → FastAPI
- Business logic → services/
- DB models → db/
- Async processing → workers/
- Storage abstraction → configurable

---

## Security (MVP)

Currently uses HTTP Basic Auth for endpoint protection.

This is intentionally simple and will be replaced with:

- JWT
- OAuth
- or API key system

before public release.

---

## Storage Strategy

Currently uses local filesystem:

- storage/uploads
- storage/results
- storage/models

Planned upgrade:

- S3-compatible object storage

The database only stores URIs, so storage backend is swappable.

---

Security Note:
No credentials or model weights are stored in this repository.
All secrets are loaded from environment variables.

---

## Deployment

Deployed on:

- VPS
- PostgreSQL
- FastAPI (Uvicorn)
- Nginx reverse proxy (planned for public exposure)

Worker runs as separate process (future: systemd service or container).

---

## Next Steps

- Add systemd service for worker + API
- Add Dockerization
- Add HTML upload UI
- Add segmentation model support
- Add GPU worker node
- Add user authentication
- Add route-building feature on top of predictions
- Add model performance dashboard

---

## Goal

The goal of this project is to demonstrate:

- Transition from ML experimentation to production systems
- Proper async job modeling
- Database-driven inference workflows
- Model lifecycle management
- Scalable architecture design
