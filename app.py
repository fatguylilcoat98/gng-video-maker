"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
import os
import logging
from typing import List, Optional
import json
import asyncio
from datetime import datetime
import threading

from modules.transcript_processor import process_transcript
from modules.voice_generator import generate_voice
from modules.presentation_builder import build_presentation
from modules.video_composer import compose_video

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='ui', static_url_path='/static')

# Enable CORS
CORS(app, origins=["*"])

# In-memory storage for demo (replace with database in production)
processing_jobs = {}

def create_processing_status(job_id, status="processing", progress=0, message="", result=None):
    """Create a processing status dictionary"""
    return {
        "id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "result": result
    }

def run_async_task(async_func, *args, **kwargs):
    """Helper to run async functions in a sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        loop.close()

def process_transcript_background(job_id, transcript, title, voice_style):
    """Background function to process transcript"""
    try:
        logger.info(f"Starting transcript processing for job {job_id}")

        # Step 1: Process transcript into structured segments
        processing_jobs[job_id]["progress"] = 20
        processing_jobs[job_id]["message"] = "Analyzing transcript structure..."

        segments = run_async_task(process_transcript, transcript, title)

        # Step 2: Generate voice narration for each segment
        processing_jobs[job_id]["progress"] = 50
        processing_jobs[job_id]["message"] = "Generating AI voiceover..."

        voice_segments = run_async_task(generate_voice, segments, voice_style)

        # Step 3: Build presentation structure
        processing_jobs[job_id]["progress"] = 80
        processing_jobs[job_id]["message"] = "Building presentation..."

        presentation = run_async_task(build_presentation, segments, voice_segments)

        # Convert presentation to dictionary for JSON serialization
        presentation_dict = {
            "id": presentation.id,
            "title": presentation.title,
            "total_duration": presentation.total_duration,
            "segments": [
                {
                    "id": seg.id,
                    "type": seg.type,
                    "title": seg.title,
                    "content": seg.content,
                    "narration_text": seg.narration_text,
                    "visual_cues": seg.visual_cues,
                    "timing": seg.timing,
                    "emphasis_level": seg.emphasis_level
                } for seg in presentation.segments
            ],
            "voice_segments": [
                {
                    "segment_id": vs.segment_id,
                    "audio_url": vs.audio_url,
                    "duration": vs.duration,
                    "voice_settings": vs.voice_settings,
                    "generated_at": vs.generated_at
                } for vs in presentation.voice_segments
            ],
            "metadata": presentation.metadata,
            "created_at": presentation.created_at
        }

        # Step 4: Prepare final composition
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["message"] = "Processing complete!"
        processing_jobs[job_id]["result"] = {
            "presentation": presentation_dict,
            "total_duration": sum(vs.duration for vs in voice_segments),
            "segment_count": len(segments)
        }

        logger.info(f"Completed processing for job {job_id}")

    except Exception as e:
        logger.error(f"Error processing transcript for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Processing failed: {str(e)}"

@app.route("/process-transcript", methods=["POST"])
def process_transcript_endpoint():
    """Process a transcript into a polished presentation"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    if not data.get("transcript"):
        abort(400, "Missing required field: transcript")

    transcript = data["transcript"]
    title = data.get("title")
    voice_style = data.get("voice_style", "professional")

    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    # Initialize job tracking
    processing_jobs[job_id] = create_processing_status(
        job_id=job_id,
        status="processing",
        progress=0,
        message="Starting transcript processing..."
    )

    # Start background processing
    thread = threading.Thread(
        target=process_transcript_background,
        args=(job_id, transcript, title, voice_style)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "processing",
        "presentation_url": f"/presentation/{job_id}"
    })

@app.route("/status/<job_id>", methods=["GET"])
def get_processing_status(job_id):
    """Get the status of a processing job"""
    if job_id not in processing_jobs:
        abort(404, "Job not found")

    return jsonify(processing_jobs[job_id])

@app.route("/presentation/<job_id>", methods=["GET"])
def get_presentation(job_id):
    """Get the completed presentation data"""
    if job_id not in processing_jobs:
        abort(404, "Job not found")

    job = processing_jobs[job_id]
    if job["status"] != "completed":
        abort(400, "Job not completed yet")

    return jsonify(job["result"])

@app.route("/compose-video", methods=["POST"])
def compose_video_endpoint():
    """Compose the final video from presentation data"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    try:
        # Convert dictionary to object-like structure
        class VideoCompositionRequest:
            def __init__(self, data):
                self.presentation_id = data.get("presentation_id")
                self.output_format = data.get("output_format", "mp4")
                self.quality = data.get("quality", "high")
                self.include_subtitles = data.get("include_subtitles", True)
                self.background_style = data.get("background_style", "professional")

        request_obj = VideoCompositionRequest(data)
        video_result = run_async_task(compose_video, request_obj)

        # Convert result to dictionary
        result_dict = {
            "video_url": video_result.video_url,
            "thumbnail_url": video_result.thumbnail_url,
            "duration": video_result.duration,
            "file_size": video_result.file_size,
            "metadata": video_result.metadata
        }

        return jsonify(result_dict)

    except Exception as e:
        logger.error(f"Error composing video: {str(e)}")
        abort(500, f"Video composition failed: {str(e)}")

@app.route("/", methods=["GET"])
def root():
    """Serve the main UI"""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "version": "1.0"})

# Serve static files
@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)