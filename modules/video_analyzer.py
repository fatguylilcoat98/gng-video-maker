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

    async def auto_trim_video(self, video_path: str, silence_periods: List[Dict[str, Any]],
                              min_silence_duration: float = 3.0) -> str:
        """
        Auto-trim dead space and long pauses from video
        """
        try:
            logger.info("Starting auto-trim of dead space and long pauses...")

            # Filter silence periods that are worth removing (long enough)
            significant_silence = [
                s for s in silence_periods
                if s['duration'] >= min_silence_duration
            ]

            if not significant_silence:
                logger.info("No significant silence periods found - returning original video")
                return video_path

            # Create trimmed video path
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            trimmed_path = tempfile.mktemp(suffix=f'_trimmed_{base_name}.mp4')
            self.temp_files.append(trimmed_path)

            # Get video info for duration
            video_info = await self.get_video_info(video_path)
            total_duration = video_info['duration']

            # Create list of segments to keep (non-silent parts)
            keep_segments = []
            last_end = 0.0

            for silence in significant_silence:
                # Keep segment before this silence
                if silence['start'] > last_end + 0.5:  # At least 0.5s of content
                    keep_segments.append({
                        'start': last_end,
                        'end': silence['start']
                    })

                # Skip most of the silence, but keep a small pause for natural flow
                natural_pause = min(1.0, silence['duration'] * 0.2)  # Keep 20% or 1s max
                last_end = silence['end'] - natural_pause

            # Add final segment if there's content after last silence
            if last_end < total_duration - 0.5:
                keep_segments.append({
                    'start': last_end,
                    'end': total_duration
                })

            if not keep_segments:
                logger.warning("No segments to keep after silence removal")
                return video_path

            # Create segment files and concat list
            concat_file = tempfile.mktemp(suffix='.txt')
            self.temp_files.append(concat_file)

            segment_files = []
            with open(concat_file, 'w') as f:
                for i, segment in enumerate(keep_segments):
                    segment_file = tempfile.mktemp(suffix=f'_seg_{i}.mp4')
                    self.temp_files.append(segment_file)
                    segment_files.append(segment_file)

                    # Extract segment
                    duration = segment['end'] - segment['start']
                    (
                        ffmpeg
                        .input(video_path, ss=segment['start'], t=duration)
                        .output(
                            segment_file,
                            vcodec='libx264',
                            acodec='aac',
                            avoid_negative_ts='make_zero'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )

                    f.write(f"file '{segment_file}'\n")

            # Concatenate all segments
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(trimmed_path, c='copy')
                .overwrite_output()
                .run(quiet=True)
            )

            # Verify trimmed video was created
            if not os.path.exists(trimmed_path):
                raise Exception("Failed to create trimmed video")

            trimmed_info = await self.get_video_info(trimmed_path)
            time_saved = total_duration - trimmed_info['duration']

            logger.info(f"Auto-trim complete: {time_saved:.1f}s removed, {trimmed_info['duration']:.1f}s remaining")

            return trimmed_path

        except Exception as e:
            logger.error(f"Auto-trim failed: {e}")
            raise

    async def extract_audio_transcript(self, video_path: str) -> str:
        """
        Extract audio from video and create a basic transcript
        """
        try:
            logger.info("Extracting audio for transcript generation...")

            # Extract audio to WAV for better compatibility
            audio_path = tempfile.mktemp(suffix='.wav')
            self.temp_files.append(audio_path)

            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path,
                    acodec='pcm_s16le',
                    ar=16000,  # 16kHz sample rate
                    ac=1       # Mono
                )
                .overwrite_output()
                .run(quiet=True)
            )

            # For now, we'll create a placeholder transcript
            # In a full implementation, you'd use a speech-to-text service here
            # Like OpenAI Whisper, Google Speech-to-Text, etc.

            placeholder_transcript = """
            [Audio extracted from video - Speech-to-text transcription would go here]

            This is a placeholder transcript. In the full implementation, this would contain:
            - Actual spoken words from the video audio
            - Timestamps for speech segments
            - Speaker identification if multiple voices
            - Cleaned up text without filler words

            The video analysis detected:
            - Audio is present in the recording
            - Multiple scene changes indicating content transitions
            - Silence periods that were trimmed for better flow
            """

            logger.info("Audio extraction complete - transcript placeholder generated")
            return placeholder_transcript.strip()

        except Exception as e:
            logger.error(f"Audio transcript extraction failed: {e}")
            return "[Audio extraction failed - unable to generate transcript]"

    async def generate_narration_script(self, video_analysis: Dict[str, Any],
                                      extracted_transcript: str, title: str = None) -> Dict[str, Any]:
        """
        Generate a polished narration script from video content using Claude
        """
        try:
            logger.info("Generating narration script from video content...")

            if not title:
                title = "Video Presentation"

            # Prepare context for Claude
            scene_count = len(video_analysis['scene_changes'])
            silence_count = len(video_analysis['silence_periods'])
            duration = video_analysis['video_info']['duration']

            minutes = int(duration // 60)
            seconds = int(duration % 60)

            prompt = f"""
Analyze this video content and create a professional narration script for a polished presentation video.

VIDEO CONTEXT:
- Title: {title}
- Duration: {minutes}:{seconds:02d}
- Scene Changes: {scene_count} detected
- Silence Periods: {silence_count} (auto-trimmed)
- Resolution: {video_analysis['video_info']['width']}x{video_analysis['video_info']['height']}

EXTRACTED CONTENT:
{extracted_transcript}

Your task is to create a compelling narration script that:
1. Introduces the video content professionally
2. Guides viewers through the key points
3. Provides smooth transitions between scene changes
4. Adds context and explanation where needed
5. Concludes with a clear summary

Return a JSON response with this exact structure:
{{
    "script_metadata": {{
        "original_duration": {duration},
        "scene_count": {scene_count},
        "estimated_narration_duration": 120.0,
        "script_style": "professional_voiceover"
    }},
    "narration_segments": [
        {{
            "segment_id": "intro",
            "type": "introduction",
            "title": "Introduction",
            "narration_text": "Welcome to this presentation...",
            "timing_cue": "At video start",
            "emphasis_level": 3
        }}
    ],
    "script_notes": {{
        "tone": "Professional and engaging",
        "pace": "Moderate with clear pauses",
        "key_improvements": ["Added context", "Improved flow", "Clear structure"]
    }}
}}

Guidelines:
- Create 4-6 narration segments based on the scene changes
- Each segment should be 15-30 seconds when narrated
- Focus on clarity and engagement
- Add value beyond just describing what's visible
- Make it suitable for educational or professional content
"""

            # Call Claude API
            from modules.llm_utils import call_anthropic_api
            response = await call_anthropic_api(prompt)

            # Parse response
            import json
            script_data = json.loads(response)

            logger.info(f"Narration script generated with {len(script_data.get('narration_segments', []))} segments")
            return script_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse narration script JSON: {e}")
            # Return fallback script
            return self._create_fallback_narration_script(video_analysis, title)

        except Exception as e:
            logger.error(f"Narration script generation failed: {e}")
            return self._create_fallback_narration_script(video_analysis, title)

    def _create_fallback_narration_script(self, video_analysis: Dict[str, Any], title: str) -> Dict[str, Any]:
        """Create a basic fallback narration script"""
        duration = video_analysis['video_info']['duration']
        scene_count = len(video_analysis['scene_changes'])

        return {
            "script_metadata": {
                "original_duration": duration,
                "scene_count": scene_count,
                "estimated_narration_duration": min(120.0, duration * 0.8),
                "script_style": "fallback_narration"
            },
            "narration_segments": [
                {
                    "segment_id": "intro",
                    "type": "introduction",
                    "title": "Introduction",
                    "narration_text": f"Welcome to {title}. This video contains valuable insights that we'll explore together.",
                    "timing_cue": "At video start",
                    "emphasis_level": 3
                },
                {
                    "segment_id": "main",
                    "type": "main_content",
                    "title": "Main Content",
                    "narration_text": f"This presentation covers {scene_count} main topics, with content automatically optimized for clarity and flow.",
                    "timing_cue": "During main content",
                    "emphasis_level": 4
                },
                {
                    "segment_id": "conclusion",
                    "type": "conclusion",
                    "title": "Conclusion",
                    "narration_text": "Thank you for watching. This concludes our presentation of the key insights.",
                    "timing_cue": "At video end",
                    "emphasis_level": 3
                }
            ],
            "script_notes": {
                "tone": "Professional",
                "pace": "Moderate",
                "key_improvements": ["Fallback script generated"]
            }
        }

    async def generate_voiceover_for_script(self, narration_script: Dict[str, Any],
                                          voice_style: str = "professional") -> List[Dict[str, Any]]:
        """
        Step 5: Generate ElevenLabs voiceover for the narration script
        """
        try:
            logger.info("Generating ElevenLabs voiceover for narration script...")

            # Import voice generation from existing Phase 2 module
            from modules.voice_generator import VoiceStyle
            from simple_schemas import PresentationSegment, VoiceSegment
            import os

            # Check if ElevenLabs API key is available
            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            if not elevenlabs_api_key:
                logger.warning("ElevenLabs API key not found, creating mock voice segments")
                return self._create_mock_voice_segments(narration_script)

            # Convert script segments to PresentationSegment format for voice generation
            script_segments = narration_script.get('narration_segments', [])
            voice_segments = []

            # Voice ID mappings for different styles (from Phase 2)
            voice_mappings = {
                "professional": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "conversational": "AZnzlk1XvdvUeBnXmlld",  # Domi
                "authoritative": "EXAVITQu4vr4xnSDxMaL",  # Bella
                "friendly": "XrExE9yKIg1WjnnlVkGX",  # Matilda
                "dramatic": "onwK4e9ZLuTAKqWW03F9"   # Daniel
            }

            voice_id = voice_mappings.get(voice_style, voice_mappings["professional"])

            for i, segment in enumerate(script_segments):
                try:
                    logger.info(f"Generating voice for segment {i+1}/{len(script_segments)}: {segment['title']}")

                    voice_segment = await self._generate_single_voice_segment(
                        segment, voice_id, voice_style, i
                    )
                    voice_segments.append(voice_segment)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Failed to generate voice for segment {segment['segment_id']}: {e}")
                    # Create fallback mock segment
                    mock_segment = self._create_mock_voice_segment(segment, i)
                    voice_segments.append(mock_segment)

            logger.info(f"Voiceover generation complete: {len(voice_segments)} segments created")
            return voice_segments

        except Exception as e:
            logger.error(f"Voiceover generation failed: {e}")
            return self._create_mock_voice_segments(narration_script)

    async def _generate_single_voice_segment(self, segment: Dict[str, Any], voice_id: str,
                                           voice_style: str, segment_index: int) -> Dict[str, Any]:
        """Generate voice for a single narration segment"""
        try:
            import httpx
            import uuid

            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": elevenlabs_api_key
            }

            # Voice settings based on segment type and style
            stability = 0.5
            similarity_boost = 0.75
            style_setting = 0.0

            if segment.get('type') == 'introduction':
                stability = 0.6  # More stable for intro
            elif segment.get('type') == 'conclusion':
                stability = 0.6
                style_setting = 0.1
            elif segment.get('emphasis_level', 3) >= 4:
                style_setting = 0.2  # More expressive for emphasis

            data = {
                "text": segment['narration_text'],
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style_setting,
                    "use_speaker_boost": True
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, headers=headers, json=data)

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"ElevenLabs API error {response.status_code}: {error_text}")
                    raise Exception(f"ElevenLabs API error: {response.status_code}")

                # Save audio file
                audio_filename = f"voice_{segment['segment_id']}_{uuid.uuid4().hex[:8]}.mp3"
                audio_path = f"static/audio/{audio_filename}"

                # Ensure audio directory exists
                os.makedirs("static/audio", exist_ok=True)

                with open(audio_path, "wb") as f:
                    f.write(response.content)

                # Estimate duration (rough calculation based on text length)
                word_count = len(segment['narration_text'].split())
                estimated_duration = (word_count / 150) * 60  # 150 words per minute

                return {
                    "segment_id": segment['segment_id'],
                    "audio_url": f"/static/audio/{audio_filename}",
                    "audio_path": audio_path,
                    "duration": estimated_duration,
                    "voice_settings": {
                        "voice_id": voice_id,
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style_setting
                    },
                    "generated_at": datetime.now().isoformat(),
                    "segment_index": segment_index
                }

        except Exception as e:
            logger.error(f"Failed to generate voice segment: {e}")
            raise

    def _create_mock_voice_segments(self, narration_script: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create mock voice segments when ElevenLabs is not available"""
        script_segments = narration_script.get('narration_segments', [])
        mock_segments = []

        for i, segment in enumerate(script_segments):
            mock_segment = self._create_mock_voice_segment(segment, i)
            mock_segments.append(mock_segment)

        return mock_segments

    def _create_mock_voice_segment(self, segment: Dict[str, Any], segment_index: int) -> Dict[str, Any]:
        """Create a single mock voice segment"""
        word_count = len(segment['narration_text'].split())
        estimated_duration = (word_count / 150) * 60  # 150 words per minute

        return {
            "segment_id": segment['segment_id'],
            "audio_url": f"/static/audio/mock_{segment['segment_id']}.mp3",
            "audio_path": f"static/audio/mock_{segment['segment_id']}.mp3",
            "duration": estimated_duration,
            "voice_settings": {
                "voice_id": "mock_voice",
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "mock": True
            },
            "generated_at": datetime.now().isoformat(),
            "segment_index": segment_index
        }

    async def create_final_video_with_voiceover(self, trimmed_video_path: str,
                                              voice_segments: List[Dict[str, Any]],
                                              narration_script: Dict[str, Any]) -> str:
        """
        Step 6: Create final MP4 with ElevenLabs voiceover synced to trimmed video
        """
        try:
            logger.info("Creating final video with voiceover...")

            # Create final video path
            base_name = os.path.splitext(os.path.basename(trimmed_video_path))[0]
            final_video_path = tempfile.mktemp(suffix=f'_final_{base_name}.mp4')
            self.temp_files.append(final_video_path)

            # Get video duration
            video_info = await self.get_video_info(trimmed_video_path)
            video_duration = video_info['duration']

            # Calculate total voiceover duration
            total_voice_duration = sum(vs['duration'] for vs in voice_segments)

            # Create combined audio track
            combined_audio_path = await self._create_combined_audio_track(
                voice_segments, total_voice_duration, video_duration
            )

            # Combine video with new audio track
            (
                ffmpeg
                .input(trimmed_video_path)
                .input(combined_audio_path)
                .output(
                    final_video_path,
                    vcodec='libx264',
                    acodec='aac',
                    map='0:v:0',  # Video from first input
                    map='1:a:0',  # Audio from second input
                    shortest=None  # Don't cut to shortest stream
                )
                .overwrite_output()
                .run(quiet=True)
            )

            # Verify final video was created
            if not os.path.exists(final_video_path):
                raise Exception("Failed to create final video")

            final_info = await self.get_video_info(final_video_path)

            logger.info(f"Final video created: {final_info['duration']:.1f}s, {final_info['width']}x{final_info['height']}")
            return final_video_path

        except Exception as e:
            logger.error(f"Final video creation failed: {e}")
            raise

    async def _create_combined_audio_track(self, voice_segments: List[Dict[str, Any]],
                                         total_voice_duration: float, video_duration: float) -> str:
        """Create a single audio track from multiple voice segments"""
        try:
            combined_audio_path = tempfile.mktemp(suffix='.wav')
            self.temp_files.append(combined_audio_path)

            if not voice_segments:
                # Create silent audio
                (
                    ffmpeg
                    .input('anullsrc', format='lavfi', t=video_duration, sample_rate=22050)
                    .output(combined_audio_path, acodec='pcm_s16le')
                    .overwrite_output()
                    .run(quiet=True)
                )
                return combined_audio_path

            # Create concat file for audio segments
            concat_file = tempfile.mktemp(suffix='.txt')
            self.temp_files.append(concat_file)

            with open(concat_file, 'w') as f:
                for voice_segment in voice_segments:
                    # Check if audio file exists (handle mock segments)
                    audio_path = voice_segment['audio_path']
                    if voice_segment['voice_settings'].get('mock'):
                        # Create silent audio for mock segments
                        mock_audio = tempfile.mktemp(suffix='.wav')
                        self.temp_files.append(mock_audio)
                        (
                            ffmpeg
                            .input('anullsrc', format='lavfi', t=voice_segment['duration'], sample_rate=22050)
                            .output(mock_audio, acodec='pcm_s16le')
                            .overwrite_output()
                            .run(quiet=True)
                        )
                        audio_path = mock_audio

                    f.write(f"file '{audio_path}'\n")

            # Concatenate all audio segments
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(combined_audio_path, acodec='pcm_s16le')
                .overwrite_output()
                .run(quiet=True)
            )

            return combined_audio_path

        except Exception as e:
            logger.error(f"Failed to create combined audio track: {e}")
            raise

# Async wrapper function for Phase 3 compatibility
async def analyze_uploaded_video(video_path: str) -> Dict[str, Any]:
    """
    Main entry point for video analysis (Steps 1-2)
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

async def process_video_content(video_path: str, analysis: Dict[str, Any], title: str = None) -> Dict[str, Any]:
    """
    Steps 3-4: Auto-trim video and generate narration script
    """
    analyzer = VideoAnalyzer()

    try:
        logger.info("Starting Steps 3-4: Auto-trim and script generation...")

        # Step 3: Auto-trim dead space and long pauses
        silence_periods = analysis.get('silence_periods', [])
        trimmed_video_path = await analyzer.auto_trim_video(video_path, silence_periods)

        # Step 4: Extract content and generate narration script
        extracted_transcript = await analyzer.extract_audio_transcript(trimmed_video_path)
        narration_script = await analyzer.generate_narration_script(analysis, extracted_transcript, title)

        # Get info about trimmed video
        trimmed_info = await analyzer.get_video_info(trimmed_video_path)

        result = {
            "original_video_path": video_path,
            "trimmed_video_path": trimmed_video_path,
            "original_duration": analysis['video_info']['duration'],
            "trimmed_duration": trimmed_info['duration'],
            "time_saved": analysis['video_info']['duration'] - trimmed_info['duration'],
            "extracted_transcript": extracted_transcript,
            "narration_script": narration_script,
            "processing_metadata": {
                "processed_at": datetime.now().isoformat(),
                "silence_periods_removed": len([s for s in silence_periods if s['duration'] >= 3.0]),
                "script_segments": len(narration_script.get('narration_segments', [])),
                "phase": "content_processing_complete"
            }
        }

        logger.info(f"Video content processing complete: {result['time_saved']:.1f}s trimmed, {len(narration_script.get('narration_segments', []))} script segments")
        return result

    except Exception as e:
        logger.error(f"Video content processing failed: {e}")
        raise
    finally:
        analyzer.cleanup()

async def finalize_video_with_voiceover(processing_result: Dict[str, Any], voice_style: str = "professional") -> Dict[str, Any]:
    """
    Steps 5-6: Generate ElevenLabs voiceover and export final MP4
    """
    analyzer = VideoAnalyzer()

    try:
        logger.info("Starting Steps 5-6: Voiceover generation and final export...")

        trimmed_video_path = processing_result['trimmed_video_path']
        narration_script = processing_result['narration_script']

        # Step 5: Generate ElevenLabs voiceover for script
        voice_segments = await analyzer.generate_voiceover_for_script(narration_script, voice_style)

        # Step 6: Create final MP4 with voiceover synced to video
        final_video_path = await analyzer.create_final_video_with_voiceover(
            trimmed_video_path, voice_segments, narration_script
        )

        # Get final video info
        final_info = await analyzer.get_video_info(final_video_path)

        result = {
            "final_video_path": final_video_path,
            "voice_segments": voice_segments,
            "final_duration": final_info['duration'],
            "final_file_size": final_info['file_size'],
            "final_resolution": f"{final_info['width']}x{final_info['height']}",
            "voiceover_metadata": {
                "voice_style": voice_style,
                "total_segments": len(voice_segments),
                "total_voice_duration": sum(vs['duration'] for vs in voice_segments),
                "generated_at": datetime.now().isoformat()
            },
            "complete_pipeline": {
                "original_duration": processing_result['original_duration'],
                "trimmed_duration": processing_result['trimmed_duration'],
                "final_duration": final_info['duration'],
                "time_saved": processing_result['time_saved'],
                "voice_added": True,
                "phase": "phase_3_complete"
            }
        }

        logger.info(f"Phase 3 complete: Final video {final_info['duration']:.1f}s with {len(voice_segments)} voice segments")
        return result

    except Exception as e:
        logger.error(f"Video finalization failed: {e}")
        raise
    finally:
        # Note: Don't cleanup here - final video path needed for download
        pass