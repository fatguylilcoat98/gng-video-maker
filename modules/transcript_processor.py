"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from simple_schemas import PresentationSegment, SegmentType
from modules.llm_utils import call_anthropic_api

logger = logging.getLogger(__name__)

# Estimation constants for transcript length detection
WORDS_PER_MINUTE = 150
BUFFER_FACTOR = 1.2  # Add 20% buffer for natural pauses

TRANSCRIPT_ANALYSIS_PROMPT = """
Analyze this transcript and break it into a polished presentation structure suitable for video narration.

TRANSCRIPT:
{transcript}

TITLE: {title}

VIDEO MODE: {video_mode}

{mode_constraints}

Your task is to:
1. Identify the main themes and key points
2. Structure the content into logical segments for video presentation
3. Create a compelling introduction that welcomes viewers and sets context (NOT raw transcript)
4. Create smooth transitions between segments
5. Suggest emphasis points for narration
6. Recommend visual cues for each segment

CRITICAL: The introduction segment should be a proper welcome/overview, not just the first part of the transcript.
CRITICAL: All narration_text should be clean, conversational, and free of markdown formatting.
CRITICAL: Respect the video mode constraints for segment count and total duration.

Return a JSON response with this exact structure:
{{
    "segments": [
        {{
            "id": "seg_001",
            "type": "introduction|main_point|transition|conclusion|emphasis",
            "title": "Segment title",
            "content": "Original transcript content for this segment",
            "narration_text": "Polished narration text optimized for voice",
            "visual_cues": ["suggested visual element 1", "suggested visual element 2"],
            "timing": {{"estimated_duration": 15.5}},
            "emphasis_level": 3
        }}
    ],
    "key_themes": ["theme1", "theme2"],
    "tone_analysis": {{
        "primary_tone": "professional",
        "energy_level": "medium",
        "complexity": "moderate"
    }},
    "suggested_structure": ["intro", "3 main points", "conclusion"],
    "estimated_duration": 180.0
}}

Guidelines:
- Each segment should be 10-30 seconds of narration
- Narration text should be conversational, professional, and completely clean (no markdown, asterisks, or formatting)
- Introduction should welcome viewers and preview what they'll learn, not just start with transcript content
- Visual cues should be specific and actionable
- Maintain the original meaning while improving flow and clarity
- Use emphasis_level (1-5) to indicate narration intensity
- Write narration as if speaking directly to the viewer
"""

SUMMARIZATION_PROMPT = """
This transcript is too long for the selected video format. Extract the 5 MOST IMPORTANT and IMPACTFUL moments that would make the best video content.

ORIGINAL TRANSCRIPT:
{transcript}

TARGET FORMAT: {video_mode}
{mode_info}

Your task:
1. Identify the 5 most engaging, valuable, or surprising moments
2. Focus on content that would hook viewers and provide real value
3. Each moment should be substantial enough for a video segment
4. Preserve the essence and impact of each moment
5. Maintain the speaker's voice and key insights

Return ONLY the 5 selected moments as a clean, flowing summary. Write each moment as a complete thought that can stand alone. Do not add commentary or explanations - just the essential content from those 5 key moments.

Format as one continuous text with the 5 moments flowing naturally together.
"""

async def process_transcript(transcript: str, title: Optional[str] = None, video_mode: str = "standard", progress_callback=None) -> List[PresentationSegment]:
    """
    Process a raw transcript into structured presentation segments
    """
    logger.info("Starting transcript processing")

    if not title:
        title = "Presentation"

    # Clean and prepare transcript
    cleaned_transcript = clean_transcript(transcript)

    # Check if summarization is needed
    if needs_summarization(cleaned_transcript, video_mode):
        if progress_callback:
            await progress_callback("Long content detected — summarizing to key moments...")

        logger.info("Transcript too long, running summarization")
        cleaned_transcript = await summarize_transcript(cleaned_transcript, video_mode)

        if progress_callback:
            await progress_callback("Summarization complete — analyzing structure...")
    else:
        if progress_callback:
            await progress_callback("Analyzing transcript structure...")

    # Get mode-specific constraints
    mode_constraints = get_mode_constraints(video_mode)

    try:
        # Call Anthropic API for analysis
        prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(
            transcript=cleaned_transcript,
            title=title,
            video_mode=video_mode,
            mode_constraints=mode_constraints
        )

        response = await call_anthropic_api(prompt)

        # Parse the JSON response
        analysis_data = json.loads(response)

        # Convert to PresentationSegment objects
        segments = []
        for seg_data in analysis_data["segments"]:
            segment = PresentationSegment(
                id=seg_data["id"],
                type=seg_data["type"],
                title=seg_data["title"],
                content=seg_data["content"],
                narration_text=seg_data["narration_text"],
                visual_cues=seg_data["visual_cues"],
                timing=seg_data["timing"],
                emphasis_level=seg_data["emphasis_level"]
            )
            segments.append(segment)

        logger.info(f"Successfully processed transcript into {len(segments)} segments")
        return segments

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse transcript analysis JSON: {e}")
        # Fallback: create basic segments
        return create_fallback_segments(cleaned_transcript, title, video_mode)

    except Exception as e:
        logger.error(f"Error processing transcript: {e}")
        # Fallback: create basic segments
        return create_fallback_segments(cleaned_transcript, title, video_mode)

def clean_transcript(transcript: str) -> str:
    """
    Clean up raw transcript text
    """
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', transcript)

    # Remove common transcript artifacts
    cleaned = re.sub(r'\[.*?\]', '', cleaned)  # Remove [timestamp] etc.
    cleaned = re.sub(r'\(.*?\)', '', cleaned)  # Remove (background noise) etc.

    # Fix common transcription issues
    cleaned = cleaned.replace(' um ', ' ')
    cleaned = cleaned.replace(' uh ', ' ')
    cleaned = cleaned.replace(' like ', ' ')

    # Clean up punctuation
    cleaned = re.sub(r'\.{2,}', '.', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned.strip()

def get_mode_constraints(video_mode: str) -> str:
    """Get mode-specific constraints for the prompt"""
    if video_mode == "shorts":
        return """
SHORTS MODE CONSTRAINTS:
- Maximum 3 segments total (including intro/outro if any)
- Total duration must not exceed 60 seconds
- Each segment should be 15-20 seconds maximum
- Text should be large, simple, and easy to read quickly
- Focus on the most impactful points only
- Optimized for mobile/vertical viewing
"""
    else:
        return """
STANDARD MODE CONSTRAINTS:
- Maximum 8 segments total
- Total duration should not exceed 180 seconds (3 minutes)
- Each segment should be 10-30 seconds
- Can include more detailed content and transitions
- Optimized for horizontal/desktop viewing
"""

def create_fallback_segments(transcript: str, title: str, video_mode: str = "standard") -> List[PresentationSegment]:
    """
    Create basic segments if AI processing fails
    """
    logger.warning("Creating fallback segments due to processing failure")

    # Split transcript into rough chunks based on video mode
    sentences = transcript.split('. ')

    if video_mode == "shorts":
        max_segments = 3
        max_duration = 60
        segment_duration = 20
    else:
        max_segments = 8
        max_duration = 180
        segment_duration = 22.5  # 180/8

    chunk_size = max(2, len(sentences) // max_segments)
    segments = []

    # Introduction segment - create proper welcome instead of raw transcript
    intro_content = '. '.join(sentences[:chunk_size])
    if video_mode == "shorts":
        intro_narration = f"Quick insights from {title}. Let's dive in!"
    else:
        intro_narration = f"Welcome to {title}. In this presentation, we'll explore the key insights and ideas from this discussion. Let's begin."

    segments.append(PresentationSegment(
        id="seg_001",
        type=SegmentType.INTRODUCTION,
        title="Introduction",
        content=intro_content,
        narration_text=intro_narration,
        visual_cues=["Title slide", "Presenter introduction"],
        timing={"estimated_duration": segment_duration},
        emphasis_level=3
    ))

    # Main content segments (respect max_segments limit)
    max_main_segments = max_segments - 2 if max_segments > 2 else max_segments - 1  # Leave room for intro and possibly conclusion
    for i in range(1, min(max_main_segments + 1, len(sentences) // chunk_size)):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, len(sentences))
        content = '. '.join(sentences[start_idx:end_idx])

        segments.append(PresentationSegment(
            id=f"seg_{i+1:03d}",
            type=SegmentType.MAIN_POINT,
            title=f"Key Point {i}",
            content=content,
            narration_text=content,
            visual_cues=["Supporting visuals", "Key point emphasis"],
            timing={"estimated_duration": segment_duration},
            emphasis_level=4
        ))

    # Conclusion segment (only if we have room and enough content)
    if len(segments) < max_segments and len(sentences) > chunk_size * 2:
        conclusion_content = '. '.join(sentences[-chunk_size:])
        conclusion_narration = "In conclusion, " + conclusion_content if video_mode != "shorts" else conclusion_content
        segments.append(PresentationSegment(
            id=f"seg_{len(segments)+1:03d}",
            type=SegmentType.CONCLUSION,
            title="Conclusion",
            content=conclusion_content,
            narration_text=conclusion_narration,
            visual_cues=["Summary slide", "Call to action"],
            timing={"estimated_duration": segment_duration},
            emphasis_level=3
        ))

    return segments

def estimate_narration_duration(text: str) -> float:
    """
    Estimate how long text will take to narrate
    Assumes average speaking rate of 150 words per minute
    """
    word_count = len(text.split())
    duration = (word_count / 150) * 60  # Convert to seconds
    return round(duration, 1)

def estimate_transcript_duration(transcript: str) -> float:
    """
    Estimate total video duration for a transcript
    """
    word_count = len(transcript.split())
    # Convert to seconds and add buffer for pauses
    duration = (word_count / WORDS_PER_MINUTE) * 60 * BUFFER_FACTOR
    return round(duration, 1)

def needs_summarization(transcript: str, video_mode: str) -> bool:
    """
    Check if transcript needs summarization based on estimated duration
    """
    estimated_duration = estimate_transcript_duration(transcript)

    if video_mode == "shorts":
        return estimated_duration > 60  # 60 seconds max for shorts
    else:
        return estimated_duration > 180  # 180 seconds (3 minutes) max for standard

async def summarize_transcript(transcript: str, video_mode: str) -> str:
    """
    Use Claude to summarize transcript to key moments
    """
    logger.info(f"Summarizing long transcript for {video_mode} mode")

    mode_info = ""
    if video_mode == "shorts":
        mode_info = "Optimizing for 60-second mobile video format. Focus on the most engaging, hook-worthy moments."
    else:
        mode_info = "Optimizing for 3-minute presentation format. Focus on substantial insights and key takeaways."

    prompt = SUMMARIZATION_PROMPT.format(
        transcript=transcript,
        video_mode=video_mode,
        mode_info=mode_info
    )

    try:
        summary = await call_anthropic_api(prompt, max_tokens=3000, temperature=0.3)
        logger.info("Transcript summarization completed")
        return summary.strip()

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        # Fallback: take first portion of transcript
        words = transcript.split()
        fallback_length = 300 if video_mode == "standard" else 150  # Rough word limits
        fallback_summary = " ".join(words[:fallback_length])
        logger.warning("Using fallback truncation instead of summarization")
        return fallback_summary