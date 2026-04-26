"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import uuid

from simple_schemas import PresentationSegment, VoiceSegment, PresentationData

logger = logging.getLogger(__name__)

async def build_presentation(
    segments: List[PresentationSegment],
    voice_segments: List[VoiceSegment],
    video_mode: str = "standard"
) -> PresentationData:
    """
    Build the final presentation structure combining content and voice
    """
    logger.info(f"Building presentation with {len(segments)} segments")

    # Create segment timing based on voice duration
    current_time = 0.0
    for i, segment in enumerate(segments):
        # Find corresponding voice segment
        voice_seg = next((vs for vs in voice_segments if vs.segment_id == segment.id), None)

        if voice_seg:
            duration = voice_seg.duration
        else:
            # Fallback duration calculation
            duration = estimate_segment_duration(segment.narration_text)

        # Update segment timing
        segment.timing = {
            "start_time": current_time,
            "duration": duration,
            "end_time": current_time + duration
        }

        current_time += duration + 0.5  # Add small gap between segments

    # Calculate total duration
    total_duration = current_time - 0.5  # Remove last gap

    # Create presentation metadata
    metadata = {
        "created_at": datetime.now().isoformat(),
        "total_segments": len(segments),
        "voice_style": voice_segments[0].voice_settings.get("style", "professional") if voice_segments else "unknown",
        "video_mode": video_mode,
        "estimated_file_size": estimate_presentation_size(segments, voice_segments),
        "themes": extract_key_themes(segments),
        "structure_analysis": analyze_presentation_structure(segments)
    }

    presentation_id = f"pres_{uuid.uuid4().hex[:12]}"

    presentation = PresentationData(
        id=presentation_id,
        title=determine_presentation_title(segments),
        total_duration=total_duration,
        segments=segments,
        voice_segments=voice_segments,
        metadata=metadata,
        created_at=datetime.now().isoformat()
    )

    logger.info(f"Presentation built successfully: {presentation_id} ({total_duration:.1f}s)")
    return presentation

def estimate_segment_duration(text: str) -> float:
    """
    Estimate duration of a text segment for narration
    """
    word_count = len(text.split())
    # Average 150 words per minute, plus pauses
    base_duration = (word_count / 150) * 60
    # Add buffer for natural pauses
    return round(base_duration * 1.2, 1)

def determine_presentation_title(segments: List[PresentationSegment]) -> str:
    """
    Determine an appropriate title for the presentation
    """
    # Check if there's an introduction segment with a clear title
    intro_segment = next((seg for seg in segments if seg.type == "introduction"), None)

    if intro_segment and len(intro_segment.title) > 3:
        return intro_segment.title

    # Extract key phrases from the first few segments
    key_phrases = []
    for segment in segments[:3]:
        words = segment.content.split()
        if len(words) > 5:
            # Take meaningful phrases
            phrases = [' '.join(words[i:i+3]) for i in range(0, min(len(words), 9), 3)]
            key_phrases.extend(phrases)

    if key_phrases:
        return key_phrases[0]

    return "GNG Presentation"

def extract_key_themes(segments: List[PresentationSegment]) -> List[str]:
    """
    Extract key themes from presentation segments
    """
    themes = []

    # Common theme keywords to look for
    theme_keywords = {
        'technology': ['tech', 'digital', 'software', 'AI', 'automation', 'innovation'],
        'business': ['market', 'revenue', 'growth', 'strategy', 'customers', 'sales'],
        'education': ['learn', 'teach', 'knowledge', 'skills', 'training', 'development'],
        'health': ['health', 'wellness', 'medical', 'fitness', 'care', 'treatment'],
        'environment': ['environment', 'sustainability', 'green', 'climate', 'eco'],
        'security': ['security', 'safety', 'protection', 'privacy', 'defense'],
        'community': ['community', 'social', 'people', 'society', 'collaboration']
    }

    # Combine all segment content
    all_content = ' '.join([seg.content.lower() for seg in segments])

    # Check for theme keywords
    for theme, keywords in theme_keywords.items():
        if any(keyword in all_content for keyword in keywords):
            themes.append(theme)

    return themes[:5]  # Limit to top 5 themes

def analyze_presentation_structure(segments: List[PresentationSegment]) -> Dict[str, Any]:
    """
    Analyze the structure and flow of the presentation
    """
    structure = {
        "has_introduction": any(seg.type == "introduction" for seg in segments),
        "has_conclusion": any(seg.type == "conclusion" for seg in segments),
        "main_points_count": len([seg for seg in segments if seg.type == "main_point"]),
        "transitions_count": len([seg for seg in segments if seg.type == "transition"]),
        "emphasis_segments": len([seg for seg in segments if seg.type == "emphasis"]),
        "average_emphasis_level": sum(seg.emphasis_level for seg in segments) / len(segments),
        "flow_quality": calculate_flow_quality(segments)
    }

    return structure

def calculate_flow_quality(segments: List[PresentationSegment]) -> str:
    """
    Calculate a qualitative assessment of presentation flow
    """
    # Check for logical progression
    has_intro = any(seg.type == "introduction" for seg in segments)
    has_conclusion = any(seg.type == "conclusion" for seg in segments)
    has_main_content = any(seg.type == "main_point" for seg in segments)

    # Check segment duration balance
    durations = [seg.timing.get("duration", 15) for seg in segments if "duration" in seg.timing]
    duration_variance = max(durations) - min(durations) if durations else 0

    # Assess quality
    if has_intro and has_conclusion and has_main_content and duration_variance < 20:
        return "excellent"
    elif (has_intro or has_conclusion) and has_main_content and duration_variance < 30:
        return "good"
    elif has_main_content:
        return "adequate"
    else:
        return "needs_improvement"

def estimate_presentation_size(
    segments: List[PresentationSegment],
    voice_segments: List[VoiceSegment]
) -> Dict[str, float]:
    """
    Estimate file sizes for the presentation
    """
    # Rough estimates in MB
    audio_size = len(voice_segments) * 0.5  # ~0.5MB per minute of audio
    video_size = sum(seg.timing.get("duration", 15) for seg in segments) / 60 * 5  # ~5MB per minute

    return {
        "audio_mb": round(audio_size, 1),
        "estimated_video_mb": round(video_size, 1),
        "total_estimated_mb": round(audio_size + video_size, 1)
    }