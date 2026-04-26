"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import logging
from typing import List, Optional
import json
import asyncio
from datetime import datetime

from modules.transcript_processor import process_transcript
from modules.voice_generator import generate_voice
from modules.presentation_builder import build_presentation
from modules.video_composer import compose_video
from schemas import (
    ProcessRequest, ProcessResponse, PresentationSegment,
    VideoCompositionRequest, VideoCompositionResponse,
    VoiceGenerationRequest, VoiceGenerationResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GNG Video Maker", version="1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="ui"), name="static")

class TranscriptRequest(BaseModel):
    transcript: str
    title: Optional[str] = None
    voice_style: Optional[str] = "professional"

class ProcessingStatus(BaseModel):
    id: str
    status: str  # processing, completed, failed
    progress: int
    message: str
    result: Optional[dict] = None

# In-memory storage for demo (replace with database in production)
processing_jobs = {}

@app.post("/process-transcript")
async def process_transcript_endpoint(request: TranscriptRequest) -> dict:
    """Process a transcript into a polished presentation"""

    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    # Initialize job tracking
    processing_jobs[job_id] = ProcessingStatus(
        id=job_id,
        status="processing",
        progress=0,
        message="Starting transcript processing..."
    )

    try:
        logger.info(f"Starting transcript processing for job {job_id}")

        # Step 1: Process transcript into structured segments
        processing_jobs[job_id].progress = 20
        processing_jobs[job_id].message = "Analyzing transcript structure..."

        segments = await process_transcript(request.transcript, request.title)

        # Step 2: Generate voice narration for each segment
        processing_jobs[job_id].progress = 50
        processing_jobs[job_id].message = "Generating AI voiceover..."

        voice_segments = await generate_voice(segments, request.voice_style)

        # Step 3: Build presentation structure
        processing_jobs[job_id].progress = 80
        processing_jobs[job_id].message = "Building presentation..."

        presentation = await build_presentation(segments, voice_segments)

        # Step 4: Prepare final composition
        processing_jobs[job_id].progress = 100
        processing_jobs[job_id].status = "completed"
        processing_jobs[job_id].message = "Processing complete!"
        processing_jobs[job_id].result = {
            "presentation": presentation,
            "total_duration": sum(seg.duration for seg in voice_segments),
            "segment_count": len(segments)
        }

        logger.info(f"Completed processing for job {job_id}")

        return {
            "job_id": job_id,
            "status": "completed",
            "presentation_url": f"/presentation/{job_id}"
        }

    except Exception as e:
        logger.error(f"Error processing transcript for job {job_id}: {str(e)}")
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Processing failed: {str(e)}"
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/status/{job_id}")
async def get_processing_status(job_id: str) -> ProcessingStatus:
    """Get the status of a processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return processing_jobs[job_id]

@app.get("/presentation/{job_id}")
async def get_presentation(job_id: str):
    """Get the completed presentation data"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = processing_jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    return job.result

@app.post("/compose-video")
async def compose_video_endpoint(request: VideoCompositionRequest) -> VideoCompositionResponse:
    """Compose the final video from presentation data"""
    try:
        video_result = await compose_video(request)
        return video_result
    except Exception as e:
        logger.error(f"Error composing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video composition failed: {str(e)}")

@app.get("/")
async def root():
    """Serve the main UI"""
    return FileResponse("ui/index.html")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)