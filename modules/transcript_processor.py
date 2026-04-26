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

TRANSCRIPT_ANALYSIS_PROMPT = """
Analyze this transcript and break it into a polished presentation structure suitable for video narration.

TRANSCRIPT:
{transcript}

TITLE: {title}

Your task is to:
1. Identify the main themes and key points
2. Structure the content into logical segments for video presentation
3. Create a compelling introduction that welcomes viewers and sets context (NOT raw transcript)
4. Create smooth transitions between segments
5. Suggest emphasis points for narration
6. Recommend visual cues for each segment

CRITICAL: The introduction segment should be a proper welcome/overview, not just the first part of the transcript.
CRITICAL: All narration_text should be clean, conversational, and free of markdown formatting.

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

async def process_transcript(transcript: str, title: Optional[str] = None) -> List[PresentationSegment]:
    """
    Process a raw transcript into structured presentation segments
    """
    logger.info("Starting transcript processing")

    if not title:
        title = "Presentation"

    # Clean and prepare transcript
    cleaned_transcript = clean_transcript(transcript)

    try:
        # Call Anthropic API for analysis
        prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(
            transcript=cleaned_transcript,
            title=title
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
        return create_fallback_segments(cleaned_transcript, title)

    except Exception as e:
        logger.error(f"Error processing transcript: {e}")
        # Fallback: create basic segments
        return create_fallback_segments(cleaned_transcript, title)

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

def create_fallback_segments(transcript: str, title: str) -> List[PresentationSegment]:
    """
    Create basic segments if AI processing fails
    """
    logger.warning("Creating fallback segments due to processing failure")

    # Split transcript into rough chunks
    sentences = transcript.split('. ')
    chunk_size = max(2, len(sentences) // 5)  # Aim for ~5 segments

    segments = []

    # Introduction segment - create proper welcome instead of raw transcript
    intro_content = '. '.join(sentences[:chunk_size])
    intro_narration = f"Welcome to {title}. In this presentation, we'll explore the key insights and ideas from this discussion. Let's begin."
    segments.append(PresentationSegment(
        id="seg_001",
        type=SegmentType.INTRODUCTION,
        title="Introduction",
        content=intro_content,
        narration_text=intro_narration,
        visual_cues=["Title slide", "Presenter introduction"],
        timing={"estimated_duration": 15.0},
        emphasis_level=3
    ))

    # Main content segments
    for i in range(1, min(4, len(sentences) // chunk_size)):
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
            timing={"estimated_duration": 20.0},
            emphasis_level=4
        ))

    # Conclusion segment
    if len(sentences) > chunk_size * 2:
        conclusion_content = '. '.join(sentences[-chunk_size:])
        segments.append(PresentationSegment(
            id=f"seg_{len(segments)+1:03d}",
            type=SegmentType.CONCLUSION,
            title="Conclusion",
            content=conclusion_content,
            narration_text="In conclusion, " + conclusion_content,
            visual_cues=["Summary slide", "Call to action"],
            timing={"estimated_duration": 12.0},
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