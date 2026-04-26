"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import os
import tempfile
import uuid
from typing import List, Dict, Any
from datetime import datetime
import asyncio
import subprocess
import shutil

import ffmpeg
from PIL import Image, ImageDraw, ImageFont
import json

logger = logging.getLogger(__name__)

# Video specifications
STANDARD_WIDTH = 1920
STANDARD_HEIGHT = 1080
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
VIDEO_FPS = 30

# GNG Color scheme
BACKGROUND_COLOR = "#0a0a0c"
TEXT_COLOR = "#ffffff"
ACCENT_GOLD = "#c8a96e"
ACCENT_GREEN = "#7ec8a9"
TEXT_MUTED = "#888888"

# Base font configurations (will be scaled based on mode)
BASE_FONT_CONFIGS = {
    "title": {"size": 72, "family": "arial"},
    "main": {"size": 48, "family": "arial"},
    "subtitle": {"size": 36, "family": "arial"},
    "caption": {"size": 24, "family": "arial"},
    "mono": {"size": 20, "family": "courier"}
}

class VideoComposer:
    def __init__(self, video_mode="standard"):
        self.temp_files = []
        self.video_mode = video_mode

        # Set dimensions based on video mode
        if video_mode == "shorts":
            self.width = SHORTS_WIDTH
            self.height = SHORTS_HEIGHT
            self.font_scale = 1.3  # Larger text for mobile viewing
        else:
            self.width = STANDARD_WIDTH
            self.height = STANDARD_HEIGHT
            self.font_scale = 1.0

    def check_ffmpeg_installation(self):
        """Check if FFmpeg is installed and accessible"""
        try:
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                raise Exception("FFmpeg not found in PATH. Please install FFmpeg.")

            logger.info(f"FFmpeg found at: {ffmpeg_path}")

            # Check version
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception(f"FFmpeg version check failed: {result.stderr}")

            logger.info(f"FFmpeg version info: {result.stdout.split(chr(10))[0]}")
            return ffmpeg_path

        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg.")
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg version check timed out.")
        except Exception as e:
            logger.error(f"FFmpeg check failed: {e}")
            raise

    def validate_input_file(self, file_path: str, file_type: str):
        """Validate that input file exists and is readable"""
        if not os.path.exists(file_path):
            raise Exception(f"{file_type} file does not exist: {file_path}")

        if not os.path.isfile(file_path):
            raise Exception(f"{file_type} path is not a file: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise Exception(f"{file_type} file is empty: {file_path}")

        logger.info(f"Validated {file_type} file: {file_path} ({file_size} bytes)")

    def get_actual_audio_duration(self, audio_path: str) -> float:
        """Get the actual duration of an audio file using FFmpeg"""
        try:
            # Use FFmpeg probe to get exact duration
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "csv=p=0", audio_path
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.info(f"Actual audio duration for {audio_path}: {duration:.2f}s")
                return duration
            else:
                logger.warning(f"Could not get audio duration for {audio_path}, using fallback")
                return 3.0  # Fallback duration

        except Exception as e:
            logger.warning(f"Error getting audio duration: {e}, using fallback")
            return 3.0  # Fallback duration

    def run_ffmpeg_command_safe(self, ffmpeg_cmd, description: str):
        """Run FFmpeg command with comprehensive error handling"""
        try:
            logger.info(f"Starting {description}")

            # Log the actual command that will be run
            cmd_args = ffmpeg_cmd.compile()
            logger.info(f"EXACT FFMPEG COMMAND: {' '.join(cmd_args)}")

            # Log each argument separately for clarity
            logger.info(f"FFmpeg arguments breakdown:")
            for i, arg in enumerate(cmd_args):
                logger.info(f"  [{i}]: {arg}")

            # Run the command and capture all output
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Log return code first
            logger.info(f"FFmpeg return code: {result.returncode}")

            # Log all output (complete, not truncated)
            if result.stdout:
                logger.info(f"FFmpeg COMPLETE STDOUT ({len(result.stdout)} chars):\n{result.stdout}")

            if result.stderr:
                logger.info(f"FFmpeg COMPLETE STDERR ({len(result.stderr)} chars):\n{result.stderr}")

            if result.returncode != 0:
                error_msg = f"{description} failed with return code {result.returncode}"
                error_msg += f"\n\nCOMPLETE COMMAND:\n{' '.join(cmd_args)}"
                if result.stderr:
                    error_msg += f"\n\nCOMPLETE STDERR:\n{result.stderr}"
                if result.stdout:
                    error_msg += f"\n\nCOMPLETE STDOUT:\n{result.stdout}"

                logger.error(f"FFMPEG FAILURE DETAILS:\n{error_msg}")
                raise Exception(error_msg)

            logger.info(f"{description} completed successfully")

        except subprocess.TimeoutExpired:
            raise Exception(f"{description} timed out after 5 minutes")
        except Exception as e:
            logger.error(f"{description} failed: {e}")
            raise

    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files = []

    def get_font(self, font_type: str):
        """Get font with fallback handling and mode-based scaling"""
        base_config = BASE_FONT_CONFIGS.get(font_type, BASE_FONT_CONFIGS["main"])
        scaled_size = int(base_config["size"] * self.font_scale)

        # Try to load custom font, fall back to default
        font_paths = [
            f"/System/Library/Fonts/{base_config['family']}.ttf",  # macOS
            f"C:/Windows/Fonts/{base_config['family']}.ttf",       # Windows
            f"/usr/share/fonts/truetype/{base_config['family']}.ttf"  # Linux
        ]

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, scaled_size)
            except Exception:
                continue

        # Ultimate fallback to default font
        try:
            return ImageFont.truetype("arial.ttf", scaled_size)
        except Exception:
            return ImageFont.load_default()

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def draw_text_centered(self, draw, text: str, y_position: int, font, color: str, max_width: int = None):
        """Draw text centered horizontally with word wrapping"""
        if max_width is None:
            max_width = self.width - 200  # Default padding

        # Word wrap if needed
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word too long, just add it
                    lines.append(word)

        if current_line:
            lines.append(" ".join(current_line))

        # Draw each line centered
        line_height = font.size + 10
        total_height = len(lines) * line_height
        start_y = y_position - (total_height // 2)

        color_rgb = self.hex_to_rgb(color)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (self.width - line_width) // 2
            y = start_y + (i * line_height)
            draw.text((x, y), line, font=font, fill=color_rgb)

    def create_intro_frame(self, title: str, author: str = None) -> str:
        """Create intro slide"""
        img = Image.new('RGB', (self.width, self.height), self.hex_to_rgb(BACKGROUND_COLOR))
        draw = ImageDraw.Draw(img)

        # Adjust positioning based on aspect ratio
        center_y = self.height // 2
        title_offset = -100 if self.video_mode == "standard" else -150

        # Title
        title_font = self.get_font("title")
        self.draw_text_centered(draw, title, center_y + title_offset, title_font, TEXT_COLOR)

        # Gold accent line under title
        line_y = center_y + title_offset + (100 if self.video_mode == "standard" else 150)
        line_width = 300 if self.video_mode == "standard" else 400
        line_x = (self.width - line_width) // 2
        line_thickness = 4 if self.video_mode == "standard" else 6
        draw.rectangle([line_x, line_y, line_x + line_width, line_y + line_thickness],
                      fill=self.hex_to_rgb(ACCENT_GOLD))

        # Author if provided
        if author:
            author_font = self.get_font("subtitle")
            author_offset = 120 if self.video_mode == "standard" else 200
            self.draw_text_centered(draw, f"by {author}", center_y + author_offset, author_font, TEXT_MUTED)

        # Save frame
        frame_path = tempfile.mktemp(suffix='.png')
        img.save(frame_path)
        self.temp_files.append(frame_path)

        return frame_path

    def create_outro_frame(self) -> str:
        """Create outro slide with GNG branding"""
        img = Image.new('RGB', (self.width, self.height), self.hex_to_rgb(BACKGROUND_COLOR))
        draw = ImageDraw.Draw(img)

        center_y = self.height // 2

        # Main GNG text
        title_font = self.get_font("title")
        main_text = "Good Neighbor Guard" if self.video_mode == "shorts" else "The Good Neighbor Guard"
        self.draw_text_centered(draw, main_text, center_y - 100, title_font, TEXT_COLOR)

        # Tagline
        subtitle_font = self.get_font("main")
        tagline = "Truth · Safety · We Got Your Back" if self.video_mode == "standard" else "Truth • Safety • We Got Your Back"
        self.draw_text_centered(draw, tagline, center_y + 50, subtitle_font, ACCENT_GREEN)

        # Save frame
        frame_path = tempfile.mktemp(suffix='.png')
        img.save(frame_path)
        self.temp_files.append(frame_path)

        return frame_path

    def create_segment_frame_from_dict(self, segment_dict: Dict, segment_number: int) -> str:
        """Create frame from segment dictionary (for JSON compatibility)"""
        img = Image.new('RGB', (self.width, self.height), self.hex_to_rgb(BACKGROUND_COLOR))
        draw = ImageDraw.Draw(img)

        # Segment number (bottom area, adjusted for mode)
        mono_font = self.get_font("mono")
        number_text = f"Segment {segment_number}"
        number_y = self.height - (80 if self.video_mode == "standard" else 120)
        draw.text((50, number_y), number_text, font=mono_font, fill=self.hex_to_rgb(TEXT_MUTED))

        # Determine accent color
        accent_color = ACCENT_GOLD
        if segment_dict.get("type") == "emphasis" or segment_dict.get("emphasis_level", 3) >= 4:
            accent_color = ACCENT_GREEN

        # Title positioning (adjusted for aspect ratio)
        title_font = self.get_font("main")
        if self.video_mode == "shorts":
            title_y = self.height // 4  # Higher on vertical layout
        else:
            title_y = self.height // 3

        title = segment_dict.get("title", "Segment")
        self.draw_text_centered(draw, title, title_y, title_font, TEXT_COLOR)

        # Accent line (adjusted size for mode)
        line_y = title_y + (80 if self.video_mode == "standard" else 120)
        line_width = min(400 if self.video_mode == "standard" else 500, len(title) * 8)
        line_x = (self.width - line_width) // 2
        line_thickness = 3 if self.video_mode == "standard" else 5
        draw.rectangle([line_x, line_y, line_x + line_width, line_y + line_thickness],
                      fill=self.hex_to_rgb(accent_color))

        # Main text (adjusted positioning and width)
        main_font = self.get_font("subtitle")
        narration = self.clean_markdown(segment_dict.get("narration_text", ""))

        if self.video_mode == "shorts":
            text_y = self.height // 2
            max_text_width = self.width - 100  # Narrower padding for mobile
        else:
            text_y = self.height // 2 + 100
            max_text_width = self.width - 200  # Standard padding

        self.draw_text_centered(draw, narration, text_y, main_font, TEXT_COLOR, max_width=max_text_width)

        # Save frame
        frame_path = tempfile.mktemp(suffix='.png')
        img.save(frame_path)
        self.temp_files.append(frame_path)

        return frame_path

    def create_enhanced_segment_frame(self, segment_dict: Dict, segment_number: int, duration: float) -> str:
        """Create enhanced frame with dynamic content and better visuals"""
        img = Image.new('RGB', (self.width, self.height), self.hex_to_rgb(BACKGROUND_COLOR))
        draw = ImageDraw.Draw(img)

        # Add subtle background pattern
        self.add_background_pattern(img)

        # Determine colors based on segment type and emphasis
        if segment_dict.get("type") == "introduction":
            accent_color = ACCENT_GOLD
            bg_accent = "#1a1520"
        elif segment_dict.get("type") == "conclusion":
            accent_color = ACCENT_GREEN
            bg_accent = "#0f1a15"
        elif segment_dict.get("emphasis_level", 3) >= 4:
            accent_color = ACCENT_GREEN
            bg_accent = "#0f1a15"
        else:
            accent_color = ACCENT_GOLD
            bg_accent = "#1a1520"

        # Add colored background accent
        accent_height = 200 if self.video_mode == "standard" else 300
        draw.rectangle([0, 0, self.width, accent_height], fill=self.hex_to_rgb(bg_accent))

        # Segment indicator (top-right)
        indicator_font = self.get_font("mono")
        indicator_text = f"{segment_number}"
        indicator_size = 80 if self.video_mode == "standard" else 100

        # Draw circle indicator
        circle_x = self.width - 120
        circle_y = 60
        circle_radius = 30 if self.video_mode == "standard" else 40
        draw.ellipse([circle_x - circle_radius, circle_y - circle_radius,
                     circle_x + circle_radius, circle_y + circle_radius],
                     fill=self.hex_to_rgb(accent_color))

        # Center number in circle
        bbox = draw.textbbox((0, 0), indicator_text, font=indicator_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = circle_x - text_width // 2
        text_y = circle_y - text_height // 2
        draw.text((text_x, text_y), indicator_text, font=indicator_font, fill=self.hex_to_rgb(BACKGROUND_COLOR))

        # Main title with better positioning
        title = segment_dict.get("title", f"Point {segment_number}")
        title_font = self.get_font("title") if len(title) < 20 else self.get_font("main")

        if self.video_mode == "shorts":
            title_y = accent_height + 80
            max_title_width = self.width - 80
        else:
            title_y = accent_height + 100
            max_title_width = self.width - 200

        self.draw_text_centered(draw, title, title_y, title_font, accent_color, max_width=max_title_width)

        # Key points from narration (extract main ideas)
        narration = segment_dict.get("narration_text", "")
        key_points = self.extract_key_points(narration)

        # Draw key points as bullet points
        if key_points:
            bullet_font = self.get_font("subtitle")
            bullet_y_start = title_y + 120 if self.video_mode == "standard" else title_y + 160
            bullet_spacing = 60 if self.video_mode == "standard" else 80

            for i, point in enumerate(key_points[:3]):  # Max 3 key points
                bullet_y = bullet_y_start + (i * bullet_spacing)
                bullet_x = 100 if self.video_mode == "standard" else 60

                # Draw bullet
                draw.ellipse([bullet_x - 8, bullet_y + 20, bullet_x + 8, bullet_y + 36],
                           fill=self.hex_to_rgb(accent_color))

                # Draw point text
                point_text = point[:80] + "..." if len(point) > 80 else point
                draw.text((bullet_x + 30, bullet_y), point_text, font=bullet_font, fill=self.hex_to_rgb(TEXT_COLOR))

        # Add progress bar at bottom
        progress_height = 8
        progress_y = self.height - 40
        progress_width = self.width - 200
        progress_x = 100

        # Background bar
        draw.rectangle([progress_x, progress_y, progress_x + progress_width, progress_y + progress_height],
                      fill=self.hex_to_rgb(TEXT_MUTED))

        # Calculate progress (rough estimate based on segment number)
        total_segments = 5  # Rough estimate
        progress = segment_number / total_segments
        filled_width = int(progress_width * min(progress, 1.0))

        if filled_width > 0:
            draw.rectangle([progress_x, progress_y, progress_x + filled_width, progress_y + progress_height],
                          fill=self.hex_to_rgb(accent_color))

        # Save frame
        frame_path = tempfile.mktemp(suffix='.png')
        img.save(frame_path)
        self.temp_files.append(frame_path)

        return frame_path

    def add_background_pattern(self, img: Image.Image):
        """Add subtle background pattern for visual interest"""
        draw = ImageDraw.Draw(img)

        # Add subtle dots pattern
        dot_color = self.hex_to_rgb("#1a1a1f")
        spacing = 60

        for y in range(0, self.height, spacing):
            for x in range(0, self.width, spacing):
                if (x + y) % 120 == 0:  # Only some dots
                    draw.ellipse([x-2, y-2, x+2, y+2], fill=dot_color)

    def extract_key_points(self, narration: str) -> List[str]:
        """Extract key points from narration text"""
        # Clean the text
        clean_text = self.clean_markdown(narration)

        # Split into sentences
        sentences = [s.strip() for s in clean_text.split('.') if s.strip()]

        # Filter for meaningful sentences (not too short)
        key_points = [s for s in sentences if len(s.split()) >= 4 and len(s) <= 100]

        # Return top 3 points
        return key_points[:3]

    def clean_markdown(self, text: str) -> str:
        """Strip markdown formatting from text"""
        import re

        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'#{1,6}\s*(.*)', r'\1', text)  # Headers
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Links
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)  # List items

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    async def compose_video(self, presentation_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """
        Compose the final video from presentation data
        """
        try:
            logger.info("Starting video composition")

            # Check FFmpeg installation first
            self.check_ffmpeg_installation()

            segments = presentation_data["segments"]
            voice_segments = presentation_data["voice_segments"]
            title = presentation_data.get("title", "GNG Presentation")

            logger.info(f"Processing {len(segments)} segments with {len(voice_segments)} voice segments")

            # Check duration limit (10 minutes = 600 seconds)
            total_duration = sum(vs["duration"] for vs in voice_segments)
            logger.info(f"Total video duration: {total_duration:.2f} seconds")

            if total_duration > 600:
                raise Exception("Video too long. Please limit presentation to 10 minutes.")

            if progress_callback:
                await progress_callback("Generating intro frame...")

            # Generate frames
            frame_paths = []
            audio_paths = []
            durations = []

            # Intro frame (3 seconds)
            logger.info("Creating intro frame")
            intro_frame = self.create_intro_frame(title)
            logger.info(f"Created intro frame: {intro_frame}")
            self.validate_input_file(intro_frame, "Intro frame")

            frame_paths.append(intro_frame)
            durations.append(3.0)

            # Create silent audio for intro
            intro_audio = tempfile.mktemp(suffix='.wav')
            logger.info(f"Creating intro audio: {intro_audio}")
            await self.create_silent_audio(intro_audio, 3.0)
            audio_paths.append(intro_audio)

            if progress_callback:
                await progress_callback("Generating content frames...")

            # Content frames
            for i, segment in enumerate(segments):
                logger.info(f"Processing content segment {i+1}: {segment.get('id', 'unknown')}")

                voice_segment = next((vs for vs in voice_segments if vs["segment_id"] == segment["id"]), None)

                if not voice_segment:
                    logger.warning(f"No voice segment found for {segment['id']}")
                    continue

                # Get actual audio duration from file instead of estimate
                audio_url = voice_segment["audio_url"]
                if audio_url.startswith("/static/"):
                    actual_audio_path = audio_url[1:]  # Remove leading slash
                else:
                    actual_audio_path = audio_url

                # Get real duration from audio file
                actual_duration = self.get_actual_audio_duration(actual_audio_path)
                logger.info(f"Voice segment estimated: {voice_segment['duration']:.2f}s, actual: {actual_duration:.2f}s")

                # Create enhanced frame with better visuals
                frame_path = self.create_enhanced_segment_frame(segment, i + 1, actual_duration)
                logger.info(f"Created frame: {frame_path}")
                self.validate_input_file(frame_path, f"Content frame {i+1}")

                frame_paths.append(frame_path)
                durations.append(actual_duration)

                # Audio file path (convert URL to local path if needed)
                audio_url = voice_segment["audio_url"]
                logger.info(f"Voice segment audio_url: {audio_url}")

                if audio_url.startswith('/static/'):
                    audio_path = audio_url[8:]  # Remove '/static/' prefix
                else:
                    audio_path = audio_url

                # Make sure we have the full path
                if not os.path.isabs(audio_path):
                    audio_path = os.path.join("static", "audio", os.path.basename(audio_path))

                logger.info(f"Resolved audio path: {audio_path}")
                self.validate_input_file(audio_path, f"Audio segment {i+1}")

                audio_paths.append(audio_path)

            # Outro frame (3 seconds)
            if progress_callback:
                await progress_callback("Generating outro frame...")

            logger.info("Creating outro frame")
            outro_frame = self.create_outro_frame()
            logger.info(f"Created outro frame: {outro_frame}")
            self.validate_input_file(outro_frame, "Outro frame")

            frame_paths.append(outro_frame)
            durations.append(3.0)

            # Create silent audio for outro
            outro_audio = tempfile.mktemp(suffix='.wav')
            logger.info(f"Creating outro audio: {outro_audio}")
            await self.create_silent_audio(outro_audio, 3.0)
            audio_paths.append(outro_audio)

            if progress_callback:
                await progress_callback("Compositing video with FFmpeg...")

            # Create video with FFmpeg
            video_path = await self.create_video_with_ffmpeg(frame_paths, audio_paths, durations)

            # Move video to permanent location
            final_video_name = f"video_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            video_dir = "static/videos"
            os.makedirs(video_dir, exist_ok=True)
            final_video_path = os.path.join(video_dir, final_video_name)

            # Copy video to permanent location
            import shutil
            shutil.move(video_path, final_video_path)
            logger.info(f"Video moved to permanent location: {final_video_path}")

            if progress_callback:
                await progress_callback("Generating thumbnail...")

            # Generate thumbnail
            thumbnail_path = await self.generate_thumbnail_for_video(title)

            if progress_callback:
                await progress_callback("Video generation complete!")

            # Calculate file size
            file_size = os.path.getsize(final_video_path) if os.path.exists(final_video_path) else 0

            return {
                "video_url": f"/download-video/{final_video_name}",
                "video_path": final_video_path,  # For internal use
                "thumbnail_url": f"/static/thumbnails/{os.path.basename(thumbnail_path)}" if thumbnail_path else "/static/assets/gng-logo.png",
                "thumbnail_path": thumbnail_path,  # For internal use
                "duration": sum(durations),
                "file_size": file_size,
                "metadata": {
                    "resolution": f"{self.width}x{self.height}",
                    "fps": VIDEO_FPS,
                    "segments_count": len(segments),
                    "video_mode": self.video_mode,
                    "generated_at": datetime.now().isoformat(),
                    "has_thumbnail": thumbnail_path is not None
                }
            }

        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            raise

    async def create_silent_audio(self, output_path: str, duration: float):
        """Create silent audio file of specified duration"""
        try:
            logger.info(f"Creating {duration}s silent audio: {output_path}")

            # Use FFmpeg to create silent audio
            cmd = (
                ffmpeg
                .input('anullsrc=r=22050', format='lavfi', t=duration)
                .output(output_path, acodec='pcm_s16le')
                .overwrite_output()
            )

            self.run_ffmpeg_command_safe(cmd, f"Silent audio creation ({duration}s)")

            # Validate the output file was created
            self.validate_input_file(output_path, "Silent audio output")
            self.temp_files.append(output_path)

        except Exception as e:
            logger.error(f"Failed to create silent audio: {e}")
            raise

    async def create_video_with_ffmpeg(self, frame_paths: List[str], audio_paths: List[str], durations: List[float]) -> str:
        """Use FFmpeg to create final video"""
        try:
            # First, check FFmpeg installation
            self.check_ffmpeg_installation()

            logger.info(f"Creating video with {len(frame_paths)} segments")

            video_path = tempfile.mktemp(suffix='.mp4')
            self.temp_files.append(video_path)

            # Create input file list for FFmpeg concat
            concat_file = tempfile.mktemp(suffix='.txt')
            self.temp_files.append(concat_file)

            segment_videos = []

            with open(concat_file, 'w') as f:
                for i, (frame_path, audio_path, duration) in enumerate(zip(frame_paths, audio_paths, durations)):
                    logger.info(f"Processing segment {i+1}/{len(frame_paths)}: {duration}s")
                    logger.info(f"Segment {i+1} inputs - Frame: {frame_path}, Audio: {audio_path}")

                    # Enhanced validation with detailed info
                    try:
                        # Frame file validation
                        if not os.path.exists(frame_path):
                            raise Exception(f"Frame file does not exist: {frame_path}")
                        frame_size = os.path.getsize(frame_path)
                        if frame_size == 0:
                            raise Exception(f"Frame file is empty: {frame_path}")
                        logger.info(f"Frame {i+1} validated: {frame_path} ({frame_size} bytes)")

                        # Audio file validation
                        if not os.path.exists(audio_path):
                            raise Exception(f"Audio file does not exist: {audio_path}")
                        audio_size = os.path.getsize(audio_path)
                        if audio_size == 0:
                            raise Exception(f"Audio file is empty: {audio_path}")
                        logger.info(f"Audio {i+1} validated: {audio_path} ({audio_size} bytes)")

                        # Additional audio format check for MP3
                        if not audio_path.lower().endswith('.mp3'):
                            logger.warning(f"Audio file is not MP3 format: {audio_path}")

                    except Exception as e:
                        logger.error(f"Input validation failed for segment {i+1}: {e}")
                        raise

                    # For each segment, create a mini video file
                    segment_video = tempfile.mktemp(suffix=f'_seg_{i}.mp4')
                    self.temp_files.append(segment_video)
                    segment_videos.append(segment_video)
                    logger.info(f"Segment {i+1} output video: {segment_video}")

                    # Create video from static image with audio
                    # Handle multiple inputs properly
                    try:
                        video_input = ffmpeg.input(frame_path, loop=1, t=duration)
                        audio_input = ffmpeg.input(audio_path)

                        cmd = ffmpeg.output(
                            video_input, audio_input,
                            segment_video,
                            vcodec='libx264',
                            acodec='aac',
                            pix_fmt='yuv420p',
                            r=VIDEO_FPS,
                            s=f'{self.width}x{self.height}'
                        ).overwrite_output()

                        logger.info(f"About to run FFmpeg for segment {i+1}")
                        self.run_ffmpeg_command_safe(cmd, f"Segment {i+1} video creation")
                        logger.info(f"FFmpeg completed for segment {i+1}")

                        # Validate segment video was created
                        if not os.path.exists(segment_video):
                            raise Exception(f"Segment video was not created: {segment_video}")
                        segment_size = os.path.getsize(segment_video)
                        if segment_size == 0:
                            raise Exception(f"Segment video is empty: {segment_video}")
                        logger.info(f"Segment {i+1} video created successfully: {segment_video} ({segment_size} bytes)")

                    except Exception as e:
                        logger.error(f"Segment {i+1} video creation failed: {e}")
                        logger.error(f"Frame path: {frame_path}")
                        logger.error(f"Audio path: {audio_path}")
                        logger.error(f"Duration: {duration}")
                        logger.error(f"Output path: {segment_video}")
                        raise

                    # Write to concat file with absolute path
                    abs_segment_path = os.path.abspath(segment_video)
                    f.write(f"file '{abs_segment_path}'\n")

            logger.info(f"Created concat file with {len(segment_videos)} segments")

            # Validate concat file was created
            self.validate_input_file(concat_file, "Concat file")

            # Log concat file contents for debugging
            with open(concat_file, 'r') as f:
                concat_contents = f.read()
                logger.info(f"Concat file contents:\n{concat_contents}")

            # Concatenate all segments
            concat_cmd = (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(video_path, c='copy')
                .overwrite_output()
            )

            self.run_ffmpeg_command_safe(concat_cmd, "Final video concatenation")

            # Validate final video was created
            self.validate_input_file(video_path, "Final video")

            logger.info(f"Video creation completed successfully: {video_path}")
            return video_path

        except Exception as e:
            logger.error(f"FFmpeg video creation failed: {e}")
            raise

    async def generate_thumbnail_for_video(self, title: str) -> str:
        """Generate thumbnail for the composed video"""
        try:
            from modules.thumbnail_generator import generate_video_thumbnail

            thumbnail_path = await generate_video_thumbnail(title, self.video_mode)
            logger.info(f"Thumbnail generated for video: {thumbnail_path}")
            return thumbnail_path

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            # Return None so video generation can continue without thumbnail
            return None

# Async wrapper function for compatibility with existing code
async def compose_video(request_data) -> Dict[str, Any]:
    """
    Main entry point for video composition
    """
    # Handle both object-style and dict-style input
    if hasattr(request_data, '__dict__'):
        # Convert object to dict
        request_dict = request_data.__dict__
    else:
        request_dict = request_data

    # Extract presentation data and video mode
    presentation_data = request_dict.get('presentation_data')
    if not presentation_data:
        raise Exception("No presentation data provided")

    # Get video mode from presentation metadata or default to standard
    video_mode = presentation_data.get('metadata', {}).get('video_mode', 'standard')

    composer = VideoComposer(video_mode=video_mode)

    try:
        result = await composer.compose_video(presentation_data)
        return result

    except Exception as e:
        logger.error(f"Video composition failed: {e}")
        raise
    finally:
        # Clean up temp files
        composer.cleanup()