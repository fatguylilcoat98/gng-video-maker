"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class VoiceStyle(str, Enum):
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    FRIENDLY = "friendly"
    DRAMATIC = "dramatic"

class SegmentType(str, Enum):
    INTRODUCTION = "introduction"
    MAIN_POINT = "main_point"
    TRANSITION = "transition"
    CONCLUSION = "conclusion"
    EMPHASIS = "emphasis"

class ProcessRequest(BaseModel):
    transcript: str
    title: Optional[str] = None
    voice_style: VoiceStyle = VoiceStyle.PROFESSIONAL
    target_duration: Optional[int] = None  # in seconds

class PresentationSegment(BaseModel):
    id: str
    type: SegmentType
    title: str
    content: str
    narration_text: str
    visual_cues: List[str]
    timing: Dict[str, float]  # start_time, duration
    emphasis_level: int  # 1-5 scale

class VoiceSegment(BaseModel):
    segment_id: str
    audio_url: str
    duration: float
    voice_settings: Dict[str, Any]
    generated_at: str

class PresentationData(BaseModel):
    id: str
    title: str
    total_duration: float
    segments: List[PresentationSegment]
    voice_segments: List[VoiceSegment]
    metadata: Dict[str, Any]
    created_at: str

class ProcessResponse(BaseModel):
    job_id: str
    status: str
    presentation_url: Optional[str] = None
    error_message: Optional[str] = None

class VoiceGenerationRequest(BaseModel):
    text: str
    voice_style: VoiceStyle
    segment_type: SegmentType
    emphasis_level: int = 3

class VoiceGenerationResponse(BaseModel):
    audio_url: str
    duration: float
    character_count: int
    voice_settings: Dict[str, Any]

class VideoCompositionRequest(BaseModel):
    presentation_id: str
    output_format: str = "mp4"
    quality: str = "high"
    include_subtitles: bool = True
    background_style: str = "professional"

class VideoCompositionResponse(BaseModel):
    video_url: str
    thumbnail_url: str
    duration: float
    file_size: int
    metadata: Dict[str, Any]

class TranscriptAnalysis(BaseModel):
    """Result of initial transcript processing"""
    segments: List[Dict[str, Any]]
    key_themes: List[str]
    tone_analysis: Dict[str, Any]
    suggested_structure: List[str]
    estimated_duration: float

class VoiceConfig(BaseModel):
    """Configuration for voice generation"""
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True

class PresentationConfig(BaseModel):
    """Configuration for presentation building"""
    max_segments: int = 20
    min_segment_duration: float = 5.0
    max_segment_duration: float = 30.0
    transition_style: str = "smooth"
    emphasis_threshold: float = 0.7