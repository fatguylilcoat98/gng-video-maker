"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import os
import asyncio
import httpx
import aiofiles
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from schemas import PresentationSegment, VoiceSegment, VoiceStyle, VoiceConfig

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# Voice ID mappings for different styles
VOICE_MAPPINGS = {
    VoiceStyle.PROFESSIONAL: "21m00Tcm4TlvDq8ikWAM",  # Rachel
    VoiceStyle.CONVERSATIONAL: "AZnzlk1XvdvUeBnXmlld",  # Domi
    VoiceStyle.AUTHORITATIVE: "EXAVITQu4vr4xnSDxMaL",  # Bella
    VoiceStyle.FRIENDLY: "XrExE9yKIg1WjnnlVkGX",  # Matilda
    VoiceStyle.DRAMATIC: "onwK4e9ZLuTAKqWW03F9"   # Daniel
}

async def generate_voice(
    segments: List[PresentationSegment],
    voice_style: str = "professional"
) -> List[VoiceSegment]:
    """
    Generate voice narration for all presentation segments
    """
    logger.info(f"Generating voice for {len(segments)} segments with {voice_style} style")

    if not ELEVENLABS_API_KEY:
        logger.warning("ELEVENLABS_API_KEY not found, creating mock voice segments")
        return create_mock_voice_segments(segments)

    voice_segments = []

    for i, segment in enumerate(segments):
        try:
            logger.info(f"Generating voice for segment {i+1}/{len(segments)}: {segment.title}")

            voice_segment = await generate_segment_voice(segment, voice_style)
            voice_segments.append(voice_segment)

            # Small delay between requests to avoid rate limiting
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to generate voice for segment {segment.id}: {e}")
            # Create fallback mock segment
            mock_segment = create_mock_voice_segment(segment)
            voice_segments.append(mock_segment)

    logger.info(f"Voice generation completed for {len(voice_segments)} segments")
    return voice_segments

async def generate_segment_voice(
    segment: PresentationSegment,
    voice_style: str
) -> VoiceSegment:
    """
    Generate voice for a single segment
    """
    voice_id = VOICE_MAPPINGS.get(VoiceStyle(voice_style), VOICE_MAPPINGS[VoiceStyle.PROFESSIONAL])

    # Configure voice settings based on segment type and emphasis
    voice_config = get_voice_config(segment, voice_style)

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    data = {
        "text": segment.narration_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": voice_config.stability,
            "similarity_boost": voice_config.similarity_boost,
            "style": voice_config.style,
            "use_speaker_boost": voice_config.use_speaker_boost
        }
    }

    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"ElevenLabs API error {response.status_code}: {error_text}")
                raise Exception(f"ElevenLabs API error: {response.status_code}")

            # Save audio file
            audio_filename = f"audio_{segment.id}_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = f"static/audio/{audio_filename}"

            # Ensure audio directory exists
            os.makedirs("static/audio", exist_ok=True)

            async with aiofiles.open(audio_path, "wb") as f:
                await f.write(response.content)

                # Estimate duration (rough calculation based on text length)
                estimated_duration = estimate_audio_duration(segment.narration_text)

                return VoiceSegment(
                    segment_id=segment.id,
                    audio_url=f"/static/audio/{audio_filename}",
                    duration=estimated_duration,
                    voice_settings=voice_config.dict(),
                    generated_at=datetime.now().isoformat()
                )

    except Exception as e:
        logger.error(f"Error generating voice for segment {segment.id}: {e}")
        raise

def get_voice_config(segment: PresentationSegment, voice_style: str) -> VoiceConfig:
    """
    Get voice configuration based on segment properties
    """
    base_config = {
        VoiceStyle.PROFESSIONAL: VoiceConfig(
            voice_id="",
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        ),
        VoiceStyle.CONVERSATIONAL: VoiceConfig(
            voice_id="",
            stability=0.3,
            similarity_boost=0.8,
            style=0.2,
            use_speaker_boost=True
        ),
        VoiceStyle.AUTHORITATIVE: VoiceConfig(
            voice_id="",
            stability=0.7,
            similarity_boost=0.7,
            style=0.1,
            use_speaker_boost=True
        ),
        VoiceStyle.FRIENDLY: VoiceConfig(
            voice_id="",
            stability=0.4,
            similarity_boost=0.85,
            style=0.3,
            use_speaker_boost=True
        ),
        VoiceStyle.DRAMATIC: VoiceConfig(
            voice_id="",
            stability=0.6,
            similarity_boost=0.6,
            style=0.8,
            use_speaker_boost=True
        )
    }

    config = base_config.get(VoiceStyle(voice_style), base_config[VoiceStyle.PROFESSIONAL])

    # Adjust based on segment emphasis level
    emphasis_multiplier = segment.emphasis_level / 3.0  # Normalize to 1.0 at level 3
    config.style = min(1.0, config.style * emphasis_multiplier)

    # Adjust based on segment type
    if segment.type == "introduction":
        config.stability = min(1.0, config.stability + 0.1)
    elif segment.type == "conclusion":
        config.stability = min(1.0, config.stability + 0.1)
        config.style = min(1.0, config.style + 0.1)
    elif segment.type == "emphasis":
        config.style = min(1.0, config.style + 0.2)
        config.similarity_boost = min(1.0, config.similarity_boost - 0.1)

    return config

def estimate_audio_duration(text: str) -> float:
    """
    Estimate audio duration based on text length
    Assumes average speaking rate of 150 words per minute
    """
    word_count = len(text.split())
    # Add some buffer for natural pauses and emphasis
    duration = (word_count / 150) * 60 * 1.2
    return round(duration, 1)

def create_mock_voice_segments(segments: List[PresentationSegment]) -> List[VoiceSegment]:
    """
    Create mock voice segments for testing when API is not available
    """
    logger.info("Creating mock voice segments for testing")

    mock_segments = []
    for segment in segments:
        mock_segment = create_mock_voice_segment(segment)
        mock_segments.append(mock_segment)

    return mock_segments

def create_mock_voice_segment(segment: PresentationSegment) -> VoiceSegment:
    """
    Create a single mock voice segment
    """
    return VoiceSegment(
        segment_id=segment.id,
        audio_url=f"/static/audio/mock_{segment.id}.mp3",
        duration=estimate_audio_duration(segment.narration_text),
        voice_settings={
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "mock": True
        },
        generated_at=datetime.now().isoformat()
    )