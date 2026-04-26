"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

class VoiceStyle:
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    FRIENDLY = "friendly"
    DRAMATIC = "dramatic"

class SegmentType:
    INTRODUCTION = "introduction"
    MAIN_POINT = "main_point"
    TRANSITION = "transition"
    CONCLUSION = "conclusion"
    EMPHASIS = "emphasis"

class PresentationSegment:
    def __init__(self, id: str, type: str, title: str, content: str,
                 narration_text: str, visual_cues: List[str],
                 timing: Dict[str, float], emphasis_level: int):
        self.id = id
        self.type = type
        self.title = title
        self.content = content
        self.narration_text = narration_text
        self.visual_cues = visual_cues
        self.timing = timing
        self.emphasis_level = emphasis_level

class VoiceSegment:
    def __init__(self, segment_id: str, audio_url: str, duration: float,
                 voice_settings: Dict[str, Any], generated_at: str):
        self.segment_id = segment_id
        self.audio_url = audio_url
        self.duration = duration
        self.voice_settings = voice_settings
        self.generated_at = generated_at

class PresentationData:
    def __init__(self, id: str, title: str, total_duration: float,
                 segments: List[PresentationSegment], voice_segments: List[VoiceSegment],
                 metadata: Dict[str, Any], created_at: str):
        self.id = id
        self.title = title
        self.total_duration = total_duration
        self.segments = segments
        self.voice_segments = voice_segments
        self.metadata = metadata
        self.created_at = created_at

class VoiceConfig:
    def __init__(self, voice_id: str, stability: float = 0.5,
                 similarity_boost: float = 0.75, style: float = 0.0,
                 use_speaker_boost: bool = True):
        self.voice_id = voice_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost

    def dict(self):
        return {
            "voice_id": self.voice_id,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost
        }