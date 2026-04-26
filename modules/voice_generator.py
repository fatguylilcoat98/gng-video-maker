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
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from simple_schemas import PresentationSegment, VoiceSegment, VoiceStyle, VoiceConfig

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

# Custom voice ID from environment (preferred) or fallback to defaults
CUSTOM_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# Voice ID mappings for different styles (fallbacks if no custom voice ID)
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

    # Check API key at runtime, not import time
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    logger.info(f"Runtime API key check: {'SET' if api_key else 'NOT SET'} ({len(api_key or '')} chars)")
    logger.info(f"Runtime Voice ID check: {'SET' if voice_id else 'NOT SET'} ({voice_id or 'none'})")

    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not found at runtime, creating mock voice segments")
        return create_mock_voice_segments(segments)

    logger.info(f"Using ElevenLabs API with {'custom' if voice_id else 'default'} voice ID")

    voice_segments = []

    for i, segment in enumerate(segments):
        try:
            logger.info(f"Generating voice for segment {i+1}/{len(segments)}: {segment.title}")

            voice_segment = await generate_segment_voice(segment, voice_style, api_key, voice_id)
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
    voice_style: str,
    api_key: str,
    custom_voice_id: str = None
) -> VoiceSegment:
    """
    Generate voice for a single segment
    """
    # Use custom voice ID if provided, otherwise use style mappings
    if custom_voice_id:
        voice_id = custom_voice_id
        logger.info(f"Using custom voice ID: {voice_id}")
    else:
        # Fix: Handle both string and enum voice styles
        if isinstance(voice_style, str):
            voice_id = VOICE_MAPPINGS.get(voice_style, VOICE_MAPPINGS[VoiceStyle.PROFESSIONAL])
        else:
            voice_id = VOICE_MAPPINGS.get(voice_style, VOICE_MAPPINGS[VoiceStyle.PROFESSIONAL])
        logger.info(f"Using default voice ID for {voice_style}: {voice_id}")

    # Configure voice settings based on segment type and emphasis
    voice_config = get_voice_config(segment, voice_style)

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
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
                logger.error(f"Request URL: {url}")
                logger.error(f"Voice ID used: {voice_id}")
                logger.error(f"Text length: {len(segment.narration_text)} characters")
                raise Exception(f"ElevenLabs API error: {response.status_code} - {error_text}")

            # Validate response contains actual audio data
            if len(response.content) < 1000:  # MP3 files should be at least 1KB
                logger.error(f"ElevenLabs API returned suspiciously small response: {len(response.content)} bytes")
                logger.error(f"Response content preview: {response.content[:200]}")
                raise Exception(f"ElevenLabs API returned invalid audio data: {len(response.content)} bytes")

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'audio' not in content_type.lower() and 'mpeg' not in content_type.lower():
                logger.error(f"ElevenLabs API returned non-audio content type: {content_type}")
                logger.error(f"Response content preview: {response.content[:200]}")
                raise Exception(f"ElevenLabs API returned non-audio content: {content_type}")

            # Save audio file
            audio_filename = f"audio_{segment.id}_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = f"static/audio/{audio_filename}"

            # Ensure audio directory exists
            os.makedirs("static/audio", exist_ok=True)

            async with aiofiles.open(audio_path, "wb") as f:
                await f.write(response.content)

            # Validate saved file
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise Exception(f"Failed to save audio file or file is empty: {audio_path}")

            logger.info(f"Successfully created ElevenLabs audio: {audio_path} ({os.path.getsize(audio_path)} bytes)")

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

    config = base_config.get(voice_style, base_config[VoiceStyle.PROFESSIONAL])

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
    Create a single mock voice segment with actual silent audio file
    """
    try:
        # Ensure audio directory exists
        os.makedirs("static/audio", exist_ok=True)

        # Create filename
        audio_filename = f"mock_{segment.id}.mp3"
        audio_path = f"static/audio/{audio_filename}"

        # Calculate duration
        duration = estimate_audio_duration(segment.narration_text)

        # Create valid audio file using FFmpeg with proper format
        # Only create if file doesn't already exist
        if not os.path.exists(audio_path):
            logger.info(f"Creating mock audio file: {audio_path} ({duration}s)")

            cmd = [
                "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=22050",
                "-t", str(duration), "-acodec", "mp3", "-ar", "22050", "-ac", "2", "-y", audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"Failed to create mock audio file: {result.stderr}")
                logger.error(f"FFmpeg command: {' '.join(cmd)}")
                # Fallback: create a minimal valid file
                duration = 1.0
                cmd = [
                    "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=22050",
                    "-t", "1", "-acodec", "mp3", "-ar", "22050", "-ac", "2", "-y", audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Fallback mock audio creation also failed: {result.stderr}")
                    raise Exception(f"Cannot create mock audio file: {result.stderr}")

            # Validate the file was created and has content
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                logger.info(f"Successfully created mock audio file: {audio_path} ({os.path.getsize(audio_path)} bytes)")
            else:
                raise Exception(f"Mock audio file creation failed or file is empty: {audio_path}")

        return VoiceSegment(
            segment_id=segment.id,
            audio_url=f"/static/audio/{audio_filename}",
            duration=duration,
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "mock": True
            },
            generated_at=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create mock voice segment: {e}")
        # Return basic segment with very short duration as fallback
        return VoiceSegment(
            segment_id=segment.id,
            audio_url=f"/static/audio/mock_{segment.id}.mp3",
            duration=1.0,
            voice_settings={"mock": True},
            generated_at=datetime.now().isoformat()
        )