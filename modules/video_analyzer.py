"""
GNG Video Maker Phase 3 — Video Analysis Module
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import os
import tempfile
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
import asyncio

import ffmpeg

logger = logging.getLogger(__name__)

# Supported video formats
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.webm', '.avi']

class VideoAnalyzer:
    def __init__(self):
        self.temp_files = []

    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files = []

    def validate_video_file(self, file_path: str) -> bool:
        """Validate if the uploaded file is a supported video format"""
        if not os.path.exists(file_path):
            return False

        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in SUPPORTED_VIDEO_FORMATS

    async def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get basic video information using FFmpeg"""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)

            if not video_stream:
                raise Exception("No video stream found in file")

            duration = float(probe['format']['duration'])
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            fps = eval(video_stream['r_frame_rate'])  # Convert fraction to float

            info = {
                "duration": duration,
                "width": width,
                "height": height,
                "fps": fps,
                "has_audio": audio_stream is not None,
                "file_size": int(probe['format']['size']),
                "format": probe['format']['format_name']
            }

            logger.info(f"Video info: {duration}s, {width}x{height}, {fps}fps")
            return info

        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise Exception(f"Unable to analyze video: {str(e)}")

    async def detect_scene_changes(self, video_path: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Detect scene changes in video using FFmpeg select filter"""
        try:
            logger.info("Starting scene change detection...")

            # Create temporary file for scene detection output
            scene_output = tempfile.mktemp(suffix='.txt')
            self.temp_files.append(scene_output)

            # Use FFmpeg select filter to detect scene changes
            # The select filter with scene change detection outputs timestamps
            (
                ffmpeg
                .input(video_path)
                .filter('select', f'gt(scene,{threshold})')
                .filter('showinfo')
                .output(scene_output, format='null')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Alternative approach: Use scene detection with metadata output
            scene_data_file = tempfile.mktemp(suffix='.json')
            self.temp_files.append(scene_data_file)

            # Run scene detection and capture metadata
            result = (
                ffmpeg
                .input(video_path)
                .filter('select', f'gt(scene,{threshold})')
                .filter('metadata', 'print:file=' + scene_data_file)
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Parse scene changes from stderr (FFmpeg outputs info there)
            scenes = self._parse_scene_changes_from_log(result.stderr.decode('utf-8'))

            logger.info(f"Detected {len(scenes)} scene changes")
            return scenes

        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            # Fallback: create artificial scenes every 30 seconds
            video_info = await self.get_video_info(video_path)
            return self._create_fallback_scenes(video_info['duration'])

    def _parse_scene_changes_from_log(self, log_output: str) -> List[Dict[str, Any]]:
        """Parse scene change timestamps from FFmpeg log output"""
        scenes = []
        lines = log_output.split('\n')

        for line in lines:
            if 'pts_time:' in line and 'scene:' in line:
                try:
                    # Extract timestamp from log line
                    timestamp_start = line.find('pts_time:') + len('pts_time:')
                    timestamp_end = line.find(' ', timestamp_start)
                    timestamp = float(line[timestamp_start:timestamp_end])

                    # Extract scene score if available
                    scene_score = 0.0
                    if 'scene:' in line:
                        score_start = line.find('scene:') + len('scene:')
                        score_end = line.find(' ', score_start)
                        if score_end == -1:
                            score_end = len(line)
                        try:
                            scene_score = float(line[score_start:score_end])
                        except:
                            scene_score = 0.0

                    scenes.append({
                        'timestamp': timestamp,
                        'scene_score': scene_score,
                        'type': 'scene_change'
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse scene timestamp: {e}")
                    continue

        # Sort by timestamp and remove duplicates
        scenes = sorted(scenes, key=lambda x: x['timestamp'])
        unique_scenes = []
        last_timestamp = -1

        for scene in scenes:
            if scene['timestamp'] - last_timestamp > 1.0:  # At least 1 second apart
                unique_scenes.append(scene)
                last_timestamp = scene['timestamp']

        return unique_scenes

    def _create_fallback_scenes(self, duration: float) -> List[Dict[str, Any]]:
        """Create fallback scene changes every 30 seconds if detection fails"""
        scenes = []
        interval = 30.0  # 30 seconds

        current_time = interval
        while current_time < duration:
            scenes.append({
                'timestamp': current_time,
                'scene_score': 0.5,  # Default score
                'type': 'fallback_scene'
            })
            current_time += interval

        logger.warning(f"Using fallback scenes: {len(scenes)} artificial scenes created")
        return scenes

    async def detect_silence_periods(self, video_path: str, silence_threshold: float = -50.0, min_duration: float = 2.0) -> List[Dict[str, Any]]:
        """Detect periods of silence in the video using FFmpeg silencedetect filter"""
        try:
            logger.info(f"Detecting silence periods (threshold: {silence_threshold}dB, min: {min_duration}s)...")

            # Run FFmpeg silencedetect filter
            result = (
                ffmpeg
                .input(video_path)
                .filter('silencedetect', n=f'{silence_threshold}dB', d=min_duration)
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Parse silence periods from stderr
            silence_periods = self._parse_silence_from_log(result.stderr.decode('utf-8'))

            logger.info(f"Detected {len(silence_periods)} silence periods")
            return silence_periods

        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            return []

    def _parse_silence_from_log(self, log_output: str) -> List[Dict[str, Any]]:
        """Parse silence periods from FFmpeg silencedetect output"""
        silence_periods = []
        lines = log_output.split('\n')

        current_silence = None

        for line in lines:
            if 'silence_start:' in line:
                try:
                    start_pos = line.find('silence_start:') + len('silence_start:')
                    end_pos = line.find(' ', start_pos)
                    if end_pos == -1:
                        end_pos = len(line)

                    start_time = float(line[start_pos:end_pos])
                    current_silence = {'start': start_time}
                except Exception as e:
                    logger.warning(f"Failed to parse silence start: {e}")

            elif 'silence_end:' in line and current_silence:
                try:
                    # Parse end time
                    end_pos = line.find('silence_end:') + len('silence_end:')
                    duration_pos = line.find(' ', end_pos)
                    end_time = float(line[end_pos:duration_pos])

                    # Parse duration
                    duration_start = line.find('silence_duration:') + len('silence_duration:')
                    duration_end = line.find(' ', duration_start)
                    if duration_end == -1:
                        duration_end = len(line)
                    duration = float(line[duration_start:duration_end])

                    silence_periods.append({
                        'start': current_silence['start'],
                        'end': end_time,
                        'duration': duration,
                        'type': 'silence'
                    })

                    current_silence = None
                except Exception as e:
                    logger.warning(f"Failed to parse silence end: {e}")

        return silence_periods

    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Complete video analysis: info + scene changes + silence detection"""
        try:
            logger.info(f"Starting complete video analysis: {video_path}")

            # Get basic video information
            video_info = await self.get_video_info(video_path)

            # Detect scene changes
            scenes = await self.detect_scene_changes(video_path)

            # Detect silence periods (only if video has audio)
            silence_periods = []
            if video_info['has_audio']:
                silence_periods = await self.detect_silence_periods(video_path)

            analysis = {
                'video_info': video_info,
                'scene_changes': scenes,
                'silence_periods': silence_periods,
                'analysis_metadata': {
                    'analyzed_at': datetime.now().isoformat(),
                    'total_scenes': len(scenes),
                    'total_silence_periods': len(silence_periods),
                    'analysis_duration': video_info['duration']
                }
            }

            logger.info(f"Video analysis complete: {len(scenes)} scenes, {len(silence_periods)} silence periods")
            return analysis

        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise

# Async wrapper function for Phase 3 compatibility
async def analyze_uploaded_video(video_path: str) -> Dict[str, Any]:
    """
    Main entry point for video analysis
    """
    analyzer = VideoAnalyzer()

    try:
        if not analyzer.validate_video_file(video_path):
            raise Exception("Invalid or unsupported video file")

        result = await analyzer.analyze_video(video_path)
        return result

    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        raise
    finally:
        analyzer.cleanup()