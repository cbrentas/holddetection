import enum
from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Text, Boolean, Enum, Float, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import uuid

class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"

class ArtifactType(str, enum.Enum):
    weights = "weights"
    plot = "plot"
    metrics = "metrics"
    other = "other"

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. s3://bucket/path or local path
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_datasets_name_version"),
        Index("ix_datasets_name", "name"),
    )

class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="created")  # created/running/succeeded/failed

    # reproducibility
    code_version: Mapped[str | None] = mapped_column(String(80), nullable=True)  # git sha
    hyperparams: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    dataset = relationship("Dataset", lazy="joined")
    artifacts = relationship("Artifact", back_populates="training_run")

    __table_args__ = (
        Index("ix_training_runs_status", "status"),
        Index("ix_training_runs_created_at", "created_at"),
    )

class Model(Base):
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(120), nullable=False)  # e.g. "hold-detector"
    version: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. "v1", "2026-03-01"
    task: Mapped[str] = mapped_column(String(30), nullable=False, default="detect")  # detect/segment
    weights_uri: Mapped[str] = mapped_column(Text, nullable=False)  # local or s3 uri

    training_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=True)

    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    training_run = relationship("TrainingRun", lazy="joined")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_models_name_version"),
        Index("ix_models_name", "name"),
        Index("ix_models_created_at", "created_at"),
    )

class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    original_uri: Mapped[str] = mapped_column(Text, nullable=False)
    original_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="upload")

    __table_args__ = (
        Index("ix_uploads_created_at", "created_at"),
    )

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.pending)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # output
    result_annotated_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    inference_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    upload = relationship("Upload", back_populates="jobs", lazy="joined")
    model = relationship("Model", lazy="joined")
    predictions = relationship("Prediction", back_populates="job")

    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_upload_id", "upload_id"),
    )

class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    class_name: Mapped[str] = mapped_column(String(80), nullable=False, default="hold")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # bbox in pixel coordinates
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    x2: Mapped[float] = mapped_column(Float, nullable=False)
    y2: Mapped[float] = mapped_column(Float, nullable=False)

    # future: segmentation polygons/masks etc
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    job = relationship("Job", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_job_id", "job_id"),
    )

class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=False)

    type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), nullable=False, default=ArtifactType.other)
    uri: Mapped[str] = mapped_column(Text, nullable=False)  # file path or s3 uri
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    training_run = relationship("TrainingRun", back_populates="artifacts")

    __table_args__ = (
        Index("ix_artifacts_training_run_id", "training_run_id"),
    )

class Wall(Base):
    __tablename__ = "walls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Wall")
    
    original_upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    latest_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    
    original_image_uri: Mapped[str] = mapped_column(Text, nullable=False)
    preview_image_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class WallHold(Base):
    __tablename__ = "wall_holds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wall_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("walls.id"), nullable=False)
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True)
    
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="model")
    class_name: Mapped[str] = mapped_column(String(80), nullable=False, default="hold")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    x2: Mapped[float] = mapped_column(Float, nullable=False)
    y2: Mapped[float] = mapped_column(Float, nullable=False)
    center_x: Mapped[float] = mapped_column(Float, nullable=False)
    center_y: Mapped[float] = mapped_column(Float, nullable=False)
    
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    label_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_user_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
