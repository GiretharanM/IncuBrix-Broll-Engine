import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    status = Column(String(32), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    current_stage = Column(String(64), nullable=False, default="Queued")

    input_type = Column(String(32), nullable=False, default="script_text")
    script_text = Column(Text, nullable=True)
    audio_url = Column(String(1024), nullable=True)
    audio_path = Column(String(1024), nullable=True)

    voice = Column(String(64), nullable=False, default="en-US-Standard")
    aspect_ratios = Column(JSON, nullable=False, default=lambda: ["16:9"])
    style = Column(String(64), nullable=False, default="cinematic")
    avoid_tags = Column(JSON, nullable=False, default=list)
    burn_in_captions = Column(Boolean, nullable=False, default=True)
    srt_captions = Column(Boolean, nullable=False, default=True)

    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    callback_url = Column(String(1024), nullable=True)

    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    warnings = Column(JSON, nullable=False, default=list)
    result_urls = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    scenes = relationship("Scene", back_populates="job", cascade="all, delete-orphan", order_by="Scene.scene_index")
    metric = relationship("JobMetric", back_populates="job", uselist=False, cascade="all, delete-orphan")


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_index = Column(Integer, nullable=False)

    text = Column(Text, nullable=False)
    visual_hint = Column(Text, nullable=True)
    visual_query = Column(Text, nullable=True)

    start_time = Column(Float, nullable=False, default=0.0)
    end_time = Column(Float, nullable=False, default=0.0)
    duration = Column(Float, nullable=False, default=0.0)

    selected_clip_id = Column(String(128), nullable=True)
    selection_reason = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    source_choice_reason = Column(Text, nullable=True)
    ai_generated = Column(Boolean, nullable=False, default=False)
    segment_hash = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    job = relationship("Job", back_populates="scenes")
    candidates = relationship("CandidateFootage", back_populates="scene", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scene_job_index", "job_id", "scene_index"),
    )


class CandidateFootage(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scene_id = Column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(32), nullable=False)  # pexels, pixabay, generative, mock
    external_id = Column(String(128), nullable=False)
    title = Column(String(256), nullable=False)
    preview_url = Column(String(1024), nullable=False)
    download_url = Column(String(1024), nullable=False)
    duration = Column(Float, nullable=False, default=0.0)
    width = Column(Integer, nullable=False, default=1920)
    height = Column(Integer, nullable=False, default=1080)

    relevance_score = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    is_selected = Column(Boolean, nullable=False, default=False)
    ai_generated = Column(Boolean, nullable=False, default=False)
    licence_name = Column(String(128), nullable=False, default="Commercial Clean")
    attribution = Column(Text, nullable=True)

    scene = relationship("Scene", back_populates="candidates")


class JobMetric(Base):
    __tablename__ = "job_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    turnaround_seconds = Column(Float, nullable=False, default=0.0)
    cost_estimate = Column(Float, nullable=False, default=0.0)
    coverage_ratio = Column(Float, nullable=False, default=1.0)
    repeat_clip_rate = Column(Float, nullable=False, default=0.0)
    avg_relevance = Column(Float, nullable=False, default=0.0)

    job = relationship("Job", back_populates="metric")
