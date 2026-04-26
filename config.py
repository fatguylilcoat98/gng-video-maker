"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import os

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Model Settings
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_VOICE_MODEL = "eleven_monolingual_v1"

# Processing Configuration
MAX_TRANSCRIPT_LENGTH = 50000  # characters
MAX_SEGMENTS = 50
MIN_SEGMENT_DURATION = 3.0  # seconds
MAX_SEGMENT_DURATION = 45.0  # seconds

# File Storage
AUDIO_STORAGE_PATH = "static/audio"
VIDEO_STORAGE_PATH = "static/videos"
THUMBNAIL_STORAGE_PATH = "static/thumbnails"

# Quality Settings
VOICE_QUALITY_SETTINGS = {
    "low": {
        "model_id": "eleven_monolingual_v1",
        "stability": 0.5,
        "similarity_boost": 0.5
    },
    "medium": {
        "model_id": "eleven_monolingual_v1",
        "stability": 0.5,
        "similarity_boost": 0.75
    },
    "high": {
        "model_id": "eleven_multilingual_v2",
        "stability": 0.4,
        "similarity_boost": 0.8
    }
}

VIDEO_QUALITY_SETTINGS = {
    "low": {
        "resolution": "720x480",
        "bitrate": "1000k",
        "framerate": 24
    },
    "medium": {
        "resolution": "1280x720",
        "bitrate": "2500k",
        "framerate": 30
    },
    "high": {
        "resolution": "1920x1080",
        "bitrate": "5000k",
        "framerate": 30
    },
    "ultra": {
        "resolution": "3840x2160",
        "bitrate": "15000k",
        "framerate": 60
    }
}

# Rate Limiting
MAX_REQUESTS_PER_MINUTE = 10
MAX_CONCURRENT_JOBS = 3

# Ensure directories exist
os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)
os.makedirs(VIDEO_STORAGE_PATH, exist_ok=True)
os.makedirs(THUMBNAIL_STORAGE_PATH, exist_ok=True)