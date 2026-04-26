"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from flask import Flask, request, jsonify, send_from_directory, abort, send_file
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

def process_transcript_background(job_id, transcript, title, voice_style, video_mode="standard"):
    """Background function to process transcript"""
    try:
        logger.info(f"Starting transcript processing for job {job_id}")

        # Check if we need summarization first
        from modules.transcript_processor import check_transcript_length
        needs_summarization, summary_reason = check_transcript_length(transcript, video_mode)

        if needs_summarization:
            processing_jobs[job_id]["progress"] = 10
            processing_jobs[job_id]["message"] = "Long content detected — summarizing to key moments..."
            processing_jobs[job_id]["summarization"] = True
            logger.info(f"Transcript needs summarization: {summary_reason}")

        # Step 1: Process transcript into structured segments
        if needs_summarization:
            processing_jobs[job_id]["progress"] = 30
            processing_jobs[job_id]["message"] = "Processing key moments into segments..."
        else:
            processing_jobs[job_id]["progress"] = 20
            processing_jobs[job_id]["message"] = "Analyzing transcript structure..."

        segments = run_async_task(process_transcript, transcript, title, video_mode)

        # Step 2: Generate voice narration for each segment
        processing_jobs[job_id]["progress"] = 60 if needs_summarization else 50
        if needs_summarization:
            processing_jobs[job_id]["message"] = "Generating AI voiceover for key moments..."
        else:
            processing_jobs[job_id]["message"] = "Generating AI voiceover..."

        voice_segments = run_async_task(generate_voice, segments, voice_style)

        # Step 3: Build presentation structure
        processing_jobs[job_id]["progress"] = 85 if needs_summarization else 80
        processing_jobs[job_id]["message"] = "Building presentation..."

        presentation = run_async_task(build_presentation, segments, voice_segments, video_mode)

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
        if needs_summarization:
            processing_jobs[job_id]["message"] = "Summarized presentation complete!"
        else:
            processing_jobs[job_id]["message"] = "Processing complete!"

        processing_jobs[job_id]["result"] = {
            "presentation": presentation_dict,
            "total_duration": sum(vs.duration for vs in voice_segments),
            "segment_count": len(segments),
            "was_summarized": needs_summarization,
            "summary_reason": summary_reason if needs_summarization else None
        }

        logger.info(f"Completed processing for job {job_id}")

    except Exception as e:
        logger.error(f"Error processing transcript for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Processing failed: {str(e)}"

def generate_video_background(job_id, presentation_data):
    """Background function to generate video"""
    try:
        logger.info(f"Starting video generation for job {job_id}")

        processing_jobs[job_id]["progress"] = 10
        processing_jobs[job_id]["message"] = "Initializing video generation..."

        # Import video composer here to avoid startup issues
        from modules.video_composer import VideoComposer

        async def progress_callback(message):
            """Update progress during video generation"""
            logger.info(f"Video generation progress: {message}")
            processing_jobs[job_id]["message"] = message
            # Update progress based on message
            if "intro" in message.lower():
                processing_jobs[job_id]["progress"] = 20
            elif "content" in message.lower():
                processing_jobs[job_id]["progress"] = 50
            elif "outro" in message.lower():
                processing_jobs[job_id]["progress"] = 70
            elif "compositing" in message.lower():
                processing_jobs[job_id]["progress"] = 85
            elif "complete" in message.lower():
                processing_jobs[job_id]["progress"] = 100

        # Create video composer instance
        composer = VideoComposer()

        try:
            # Generate video
            result = run_async_task(composer.compose_video, presentation_data, progress_callback)

            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["progress"] = 100
            processing_jobs[job_id]["message"] = "Video generation complete!"
            processing_jobs[job_id]["result"] = result

            logger.info(f"Video generation completed for job {job_id}")

        finally:
            # Clean up temp files
            composer.cleanup()

    except Exception as e:
        logger.error(f"Error generating video for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Video generation failed: {str(e)}"

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
    video_mode = data.get("video_mode", "standard")

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
        args=(job_id, transcript, title, voice_style, video_mode)
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

@app.route("/generate-video", methods=["POST"])
def generate_video_endpoint():
    """Generate video from completed presentation data"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    # Get presentation data from either job_id or direct data
    if "job_id" in data:
        # Get presentation from completed job
        job_id = data["job_id"]
        if job_id not in processing_jobs:
            abort(404, "Presentation job not found")

        job = processing_jobs[job_id]
        if job["status"] != "completed":
            abort(400, "Presentation not completed yet")

        presentation_data = job["result"]["presentation"]
    elif "presentation_data" in data:
        # Use provided presentation data
        presentation_data = data["presentation_data"]
    else:
        abort(400, "Missing job_id or presentation_data")

    # Create video generation job
    video_job_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    # Initialize video job tracking
    processing_jobs[video_job_id] = create_processing_status(
        job_id=video_job_id,
        status="processing",
        progress=0,
        message="Starting video generation..."
    )

    # Start background video generation
    thread = threading.Thread(
        target=generate_video_background,
        args=(video_job_id, presentation_data)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "job_id": video_job_id,
        "status": "processing",
        "video_status_url": f"/status/{video_job_id}"
    })

@app.route("/download-video/<filename>")
def download_video(filename):
    """Download generated video file"""
    try:
        # Find the job with this video filename
        video_path = None
        for job_id, job_data in processing_jobs.items():
            if (job_data.get("status") == "completed" and
                job_data.get("result") and
                job_data["result"].get("video_path")):

                job_video_path = job_data["result"]["video_path"]
                if os.path.basename(job_video_path) == filename:
                    video_path = job_video_path
                    break

        if not video_path or not os.path.exists(video_path):
            abort(404, "Video file not found")

        return send_file(
            video_path,
            as_attachment=True,
            download_name=f"gng_video_{filename}",
            mimetype='video/mp4'
        )

    except Exception as e:
        logger.error(f"Error downloading video {filename}: {str(e)}")
        abort(500, "Failed to download video")

@app.route("/compose-video", methods=["POST"])
def compose_video_endpoint():
    """Legacy endpoint - redirects to new video generation system"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    # Redirect to new video generation endpoint
    return generate_video_endpoint()

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