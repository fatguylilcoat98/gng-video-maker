"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

from flask import Flask, request, jsonify, send_from_directory, abort, send_file
from werkzeug.utils import secure_filename
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

# ============================================================================
# PHASE 3: VIDEO UPLOAD AND ANALYSIS ENDPOINTS
# ============================================================================

def analyze_video_background(job_id, video_path):
    """Background function to analyze uploaded video"""
    try:
        logger.info(f"Starting video analysis for job {job_id}")

        processing_jobs[job_id]["progress"] = 20
        processing_jobs[job_id]["message"] = "Analyzing video properties..."

        # Import analyzer here to avoid startup issues
        from modules.video_analyzer import analyze_uploaded_video

        # Run video analysis
        analysis_result = run_async_task(analyze_uploaded_video, video_path)

        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["message"] = "Video analysis complete!"
        processing_jobs[job_id]["result"] = {
            "analysis": analysis_result,
            "video_path": video_path,
            "phase": "analysis_complete"
        }

        logger.info(f"Video analysis completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error analyzing video for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Video analysis failed: {str(e)}"

@app.route("/upload-video", methods=["POST"])
def upload_video_endpoint():
    """Phase 3: Upload and analyze video file"""

    if 'video' not in request.files:
        abort(400, "No video file uploaded")

    file = request.files['video']
    if file.filename == '':
        abort(400, "No file selected")

    # Validate file type
    allowed_extensions = {'.mp4', '.mov', '.webm', '.avi'}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        abort(400, f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}")

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"

        # Create upload directory
        upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        video_path = os.path.join(upload_dir, safe_filename)
        file.save(video_path)

        # Create analysis job
        job_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Initialize job tracking
        processing_jobs[job_id] = create_processing_status(
            job_id=job_id,
            status="processing",
            progress=0,
            message="Video uploaded, starting analysis..."
        )

        # Start background analysis
        thread = threading.Thread(
            target=analyze_video_background,
            args=(job_id, video_path)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "message": "Video uploaded successfully, analysis started",
            "filename": safe_filename,
            "analysis_url": f"/video-analysis/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        abort(500, f"Video upload failed: {str(e)}")

@app.route("/video-analysis/<job_id>", methods=["GET"])
def get_video_analysis(job_id):
    """Get video analysis results"""
    if job_id not in processing_jobs:
        abort(404, "Analysis job not found")

    job = processing_jobs[job_id]
    if job["status"] != "completed":
        # Return current status if not complete
        return jsonify({
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"]
        })

    return jsonify(job["result"])

def process_video_content_background(job_id, video_path, analysis_data, title):
    """Background function for Steps 3-4: Auto-trim and script generation"""
    try:
        logger.info(f"Starting video content processing for job {job_id}")

        processing_jobs[job_id]["progress"] = 30
        processing_jobs[job_id]["message"] = "Auto-trimming dead space and long pauses..."

        # Import processor here to avoid startup issues
        from modules.video_analyzer import process_video_content

        # Run Steps 3-4
        processing_result = run_async_task(process_video_content, video_path, analysis_data, title)

        processing_jobs[job_id]["progress"] = 60
        processing_jobs[job_id]["message"] = "Generating narration script with Claude..."

        # Complete processing
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["message"] = "Video processing complete!"
        processing_jobs[job_id]["result"] = {
            "processing": processing_result,
            "phase": "ready_for_final_steps"
        }

        logger.info(f"Video content processing completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error processing video content for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Video processing failed: {str(e)}"

@app.route("/process-video-content", methods=["POST"])
def process_video_content_endpoint():
    """Phase 3 Steps 3-4: Auto-trim video and generate narration script"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    # Get required data
    analysis_job_id = data.get("analysis_job_id")
    title = data.get("title", "Video Presentation")

    if not analysis_job_id or analysis_job_id not in processing_jobs:
        abort(400, "Invalid or missing analysis job ID")

    analysis_job = processing_jobs[analysis_job_id]
    if analysis_job["status"] != "completed":
        abort(400, "Analysis job not completed")

    try:
        # Get analysis data and video path
        analysis_data = analysis_job["result"]["analysis"]
        video_path = analysis_job["result"]["video_path"]

        # Create processing job
        job_id = f"process_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Initialize job tracking
        processing_jobs[job_id] = create_processing_status(
            job_id=job_id,
            status="processing",
            progress=0,
            message="Starting video content processing..."
        )

        # Start background processing
        thread = threading.Thread(
            target=process_video_content_background,
            args=(job_id, video_path, analysis_data, title)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "message": "Video content processing started",
            "processing_url": f"/video-processing/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error starting video content processing: {str(e)}")
        abort(500, f"Failed to start processing: {str(e)}")

@app.route("/video-processing/<job_id>", methods=["GET"])
def get_video_processing_status(job_id):
    """Get video content processing status and results"""
    if job_id not in processing_jobs:
        abort(404, "Processing job not found")

    job = processing_jobs[job_id]
    if job["status"] != "completed":
        # Return current status if not complete
        return jsonify({
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"]
        })

    return jsonify(job["result"])

def finalize_video_background(job_id, processing_result, voice_style):
    """Background function for Steps 5-6: Voiceover and final export"""
    try:
        logger.info(f"Starting video finalization for job {job_id}")

        processing_jobs[job_id]["progress"] = 20
        processing_jobs[job_id]["message"] = "Generating ElevenLabs voiceover..."

        # Import finalizer here to avoid startup issues
        from modules.video_analyzer import finalize_video_with_voiceover

        # Run Steps 5-6
        finalization_result = run_async_task(finalize_video_with_voiceover, processing_result, voice_style)

        processing_jobs[job_id]["progress"] = 80
        processing_jobs[job_id]["message"] = "Creating final MP4..."

        # Complete processing
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["message"] = "Phase 3 complete! Video ready for download."
        processing_jobs[job_id]["result"] = {
            "finalization": finalization_result,
            "download_url": f"/download-phase3-video/{os.path.basename(finalization_result['final_video_path'])}",
            "phase": "phase_3_complete"
        }

        logger.info(f"Video finalization completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error finalizing video for job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"Video finalization failed: {str(e)}"

@app.route("/finalize-video", methods=["POST"])
def finalize_video_endpoint():
    """Phase 3 Steps 5-6: Generate voiceover and export final MP4"""

    if not request.is_json:
        abort(400, "Request must be JSON")

    data = request.get_json()

    # Get required data
    processing_job_id = data.get("processing_job_id")
    voice_style = data.get("voice_style", "professional")

    if not processing_job_id or processing_job_id not in processing_jobs:
        abort(400, "Invalid or missing processing job ID")

    processing_job = processing_jobs[processing_job_id]
    if processing_job["status"] != "completed":
        abort(400, "Processing job not completed")

    try:
        # Get processing result
        processing_result = processing_job["result"]["processing"]

        # Create finalization job
        job_id = f"final_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Initialize job tracking
        processing_jobs[job_id] = create_processing_status(
            job_id=job_id,
            status="processing",
            progress=0,
            message="Starting video finalization..."
        )

        # Start background finalization
        thread = threading.Thread(
            target=finalize_video_background,
            args=(job_id, processing_result, voice_style)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "message": "Video finalization started",
            "finalization_url": f"/video-finalization/{job_id}"
        })

    except Exception as e:
        logger.error(f"Error starting video finalization: {str(e)}")
        abort(500, f"Failed to start finalization: {str(e)}")

@app.route("/video-finalization/<job_id>", methods=["GET"])
def get_video_finalization_status(job_id):
    """Get video finalization status and results"""
    if job_id not in processing_jobs:
        abort(404, "Finalization job not found")

    job = processing_jobs[job_id]
    if job["status"] != "completed":
        # Return current status if not complete
        return jsonify({
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"]
        })

    return jsonify(job["result"])

@app.route("/download-phase3-video/<filename>")
def download_phase3_video(filename):
    """Download Phase 3 finalized video file"""
    try:
        # Find the job with this video filename
        video_path = None
        for job_id, job_data in processing_jobs.items():
            if (job_data.get("status") == "completed" and
                job_data.get("result") and
                job_data["result"].get("finalization") and
                job_data["result"]["finalization"].get("final_video_path")):

                job_video_path = job_data["result"]["finalization"]["final_video_path"]
                if os.path.basename(job_video_path) == filename:
                    video_path = job_video_path
                    break

        if not video_path or not os.path.exists(video_path):
            abort(404, "Video file not found")

        return send_file(
            video_path,
            as_attachment=True,
            download_name=f"gng_phase3_{filename}",
            mimetype='video/mp4'
        )

    except Exception as e:
        logger.error(f"Error downloading Phase 3 video {filename}: {str(e)}")
        abort(500, "Failed to download video")

@app.route("/download-thumbnail/<filename>")
def download_thumbnail(filename):
    """Download thumbnail image file"""
    try:
        thumbnail_path = os.path.join("static/thumbnails", filename)

        if not os.path.exists(thumbnail_path):
            abort(404, "Thumbnail file not found")

        return send_file(
            thumbnail_path,
            as_attachment=True,
            download_name=f"gng_thumbnail_{filename}",
            mimetype='image/jpeg'
        )

    except Exception as e:
        logger.error(f"Error downloading thumbnail {filename}: {str(e)}")
        abort(500, "Failed to download thumbnail")

@app.route("/", methods=["GET"])
def root():
    """Serve the main UI"""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "version": "1.0"})

@app.route("/debug/ffmpeg", methods=["GET"])
def debug_ffmpeg():
    """Debug endpoint to check FFmpeg installation"""
    import subprocess
    import shutil

    try:
        # Check if FFmpeg is in PATH
        ffmpeg_path = shutil.which("ffmpeg")

        debug_info = {
            "ffmpeg_in_path": ffmpeg_path is not None,
            "ffmpeg_path": ffmpeg_path,
            "path_env": os.environ.get("PATH", ""),
        }

        if ffmpeg_path:
            try:
                # Get version info
                result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
                debug_info["version_check"] = {
                    "return_code": result.returncode,
                    "stdout": result.stdout.split('\n')[0] if result.stdout else "",
                    "stderr": result.stderr[:500] if result.stderr else ""
                }
            except Exception as e:
                debug_info["version_check"] = {"error": str(e)}

        # Test video composer FFmpeg check
        try:
            from modules.video_composer import VideoComposer
            composer = VideoComposer()
            composer.check_ffmpeg_installation()
            debug_info["video_composer_check"] = "SUCCESS"
        except Exception as e:
            debug_info["video_composer_check"] = f"ERROR: {str(e)}"

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/voice", methods=["GET"])
def debug_voice():
    """Debug endpoint to check voice generation setup"""
    try:
        debug_info = {
            "elevenlabs_api_key_set": bool(os.getenv("ELEVENLABS_API_KEY")),
            "elevenlabs_api_key_length": len(os.getenv("ELEVENLABS_API_KEY", "")),
            "elevenlabs_voice_id_set": bool(os.getenv("ELEVENLABS_VOICE_ID")),
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "not_set"),
        }

        # Test voice generation setup
        try:
            from modules.voice_generator import ELEVENLABS_API_KEY, ELEVENLABS_API_URL, CUSTOM_VOICE_ID
            debug_info["voice_module_api_key_set"] = bool(ELEVENLABS_API_KEY)
            debug_info["voice_module_api_url"] = ELEVENLABS_API_URL
            debug_info["voice_module_custom_voice_id"] = CUSTOM_VOICE_ID or "not_set"
        except Exception as e:
            debug_info["voice_module_error"] = str(e)

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug/test-voice", methods=["GET", "POST"])
def test_voice_generation():
    """Test voice generation with a simple segment"""
    try:
        import os

        # First check environment
        api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        debug_info = {
            "api_key_set": bool(api_key),
            "api_key_length": len(api_key) if api_key else 0,
            "voice_id_set": bool(voice_id),
            "voice_id": voice_id if voice_id else "not_set",
            "test_status": "starting"
        }

        if not api_key:
            debug_info["error"] = "ELEVENLABS_API_KEY not found"
            return jsonify(debug_info)

        # Try to import and test
        try:
            from modules.voice_generator import generate_voice
            debug_info["import_success"] = True
        except Exception as e:
            debug_info["import_error"] = str(e)
            return jsonify(debug_info)

        try:
            from simple_schemas import PresentationSegment
            debug_info["schema_import_success"] = True
        except Exception as e:
            debug_info["schema_import_error"] = str(e)
            return jsonify(debug_info)

        # Create test segment with all required fields
        try:
            test_segment = PresentationSegment(
                id="test_001",
                type="test",
                title="Test Voice Generation",
                content="Test content for voice generation",
                narration_text="This is a test of ElevenLabs voice generation.",
                visual_cues=["text"],
                timing={"start": 0.0, "duration": 3.0},
                emphasis_level=3
            )
            debug_info["segment_created"] = True

            # Now try voice generation
            async def test_voice():
                try:
                    result = await generate_voice([test_segment], "professional")
                    return {"success": True, "segments": len(result), "first_audio_url": result[0].audio_url if result else None}
                except Exception as e:
                    return {"error": str(e), "success": False}

            voice_result = run_async_task(test_voice)
            debug_info["voice_generation"] = voice_result

        except Exception as e:
            debug_info["segment_error"] = str(e)
            return jsonify(debug_info)

        debug_info["status"] = "ready_to_test"
        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"error": str(e)})

# Serve static files
@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)