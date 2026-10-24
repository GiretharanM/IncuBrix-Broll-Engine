from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

class SceneInput(BaseModel):
    text: str = Field(..., min_length=1, description="Narration text for this scene")
    visual_hint: Optional[str] = Field(None, description="Optional direction or keywords for footage matching")

class JobCreateRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="One short idea/prompt for instant video creation (e.g. 'cat walking')")
    duration_seconds: Optional[int] = Field(20, ge=8, le=60, description="Target video duration in seconds (8-60)")
    narration: Optional[bool] = Field(False, description="Whether to synthesize narration voiceover or produce an ambient video")
    seed: Optional[int] = Field(None, description="Random seed for reproducible prompt expansion and visual variations")
    scene_captions_without_narration: Optional[bool] = Field(False, description="Use scene text as subtitles when narration is disabled")
    script_text: Optional[str] = Field(None, description="Full script text to be spoken via TTS")
    audio_url: Optional[str] = Field(None, description="URL of pre-recorded voiceover audio file")
    scenes: Optional[List[SceneInput]] = Field(None, description="Pre-segmented scene list")
    voice: str = Field("en-US-Standard", description="TTS voice identifier (supports EN, HI, TA)")
    aspect_ratios: List[str] = Field(default_factory=lambda: ["16:9"], description="Target video aspect ratios (16:9, 9:16, 1:1)")
    style: str = Field("cinematic", description="Visual aesthetic style preset or prompt")
    avoid: List[str] = Field(default_factory=list, description="Visual tags or topics to exclude")
    burn_in_captions: bool = Field(True, description="Whether to burn ASS subtitles directly onto the video")
    srt_captions: bool = Field(True, description="Whether to generate and output an SRT file")
    callback_url: Optional[str] = Field(None, description="Webhook URL for signed completion notifications")

class JobCreateResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial status, usually 'queued'")
    message: str = Field("Job accepted and queued for processing", description="Human-readable response summary")

class SceneCandidateResponse(BaseModel):
    id: str
    provider: str
    external_id: str
    title: str
    preview_url: str
    download_url: str
    duration: float
    relevance_score: float
    reason: Optional[str] = None
    is_selected: bool = False
    ai_generated: bool = False
    licence_name: str
    attribution: Optional[str] = None

class SceneResponse(BaseModel):
    scene_id: str
    scene_index: int
    text: str
    visual_hint: Optional[str] = None
    visual_query: Optional[str] = None
    start_time: float
    end_time: float
    duration: float
    selected_clip_id: Optional[str] = None
    selection_reason: Optional[str] = None
    relevance_score: Optional[float] = None
    source_choice_reason: Optional[str] = None
    ai_generated: bool = False
    segment_hash: Optional[str] = None
    preview_url: Optional[str] = None
    provider: Optional[str] = None
    link: Optional[str] = None
    licence: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    current_stage: str
    aspect_ratios: List[str]
    scenes: List[SceneResponse] = Field(default_factory=list)
    result_urls: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SwapClipRequest(BaseModel):
    candidate_id: Optional[str] = Field(None, description="ID of CandidateFootage from GET candidates")
    clip_url: Optional[str] = Field(None, description="Direct URL of user-provided replacement clip")

class SwapClipResponse(BaseModel):
    job_id: str
    scene_id: str
    new_clip_id: str
    time_saved_seconds: float
    re_render_duration_seconds: float
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"

class ReadyResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
    minio: bool
    providers: Dict[str, bool] = Field(default_factory=dict)

class JobListItemResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    input_type: str
    script_preview: Optional[str] = None
    aspect_ratios: List[str] = Field(default_factory=lambda: ["16:9"])
    duration_seconds: float = 0.0
    cost_estimate_usd: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None

class JobMetricsResponse(BaseModel):
    total_jobs: int = 0
    succeeded_jobs: int = 0
    failed_jobs: int = 0
    avg_turnaround_seconds: float = 0.0
    cost_per_minute_usd: float = 0.0
    narration_coverage_ratio: float = 1.0
    avg_relevance_score: float = 0.85
    repeat_clip_rate: float = 0.0
    success_rate_percent: float = 100.0
    source_distribution: Dict[str, float] = Field(default_factory=dict)
    ratio_distribution: Dict[str, float] = Field(default_factory=dict)

