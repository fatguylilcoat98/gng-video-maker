"""
GNG Video Maker — Thumbnail Generator Module
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import os
import tempfile
from typing import Tuple, Optional
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import uuid

logger = logging.getLogger(__name__)

# GNG Color scheme
BACKGROUND_COLOR = "#0a0a0c"
TEXT_COLOR = "#ffffff"
ACCENT_GOLD = "#c8a96e"
TEXT_MUTED = "#888888"

# Thumbnail dimensions
STANDARD_WIDTH = 1280
STANDARD_HEIGHT = 720
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920

class ThumbnailGenerator:
    def __init__(self, video_mode: str = "standard"):
        self.video_mode = video_mode
        self.temp_files = []

        # Set dimensions based on video mode
        if video_mode == "shorts":
            self.width = SHORTS_WIDTH
            self.height = SHORTS_HEIGHT
            self.font_scale = 1.1  # Slightly larger for mobile
            self.logo_size = 120   # Larger logo for vertical format
        else:
            self.width = STANDARD_WIDTH
            self.height = STANDARD_HEIGHT
            self.font_scale = 1.0
            self.logo_size = 100

    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")
        self.temp_files = []

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def get_font(self, size: int, bold: bool = False):
        """Get font with fallback handling"""
        scaled_size = int(size * self.font_scale)

        # Font paths to try
        font_paths = [
            # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            # macOS
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]

        # If bold requested, try bold variants first
        if bold:
            bold_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "C:/Windows/Fonts/segoeuib.ttf",
                "/System/Library/Fonts/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ]
            font_paths = bold_paths + font_paths

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, scaled_size)
            except Exception:
                continue

        # Ultimate fallback
        try:
            return ImageFont.load_default()
        except Exception:
            # If even default fails, create a minimal font object
            return None

    def draw_text_with_wrap(self, draw, text: str, x: int, y: int, font, color: str,
                           max_width: int, line_spacing: int = 10, center: bool = True):
        """Draw text with word wrapping and optional centering"""
        words = text.split()
        lines = []
        current_line = []

        color_rgb = self.hex_to_rgb(color)

        # Word wrap
        for word in words:
            test_line = " ".join(current_line + [word])
            if font:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            else:
                # Fallback width estimation
                line_width = len(test_line) * 12

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

        if current_line:
            lines.append(" ".join(current_line))

        # Draw lines
        current_y = y
        for line in lines:
            if center:
                if font:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                else:
                    line_width = len(line) * 12
                line_x = x - (line_width // 2)
            else:
                line_x = x

            if font:
                draw.text((line_x, current_y), line, font=font, fill=color_rgb)
            else:
                # Fallback text drawing (very basic)
                draw.text((line_x, current_y), line, fill=color_rgb)

            current_y += (font.size if font else 20) + line_spacing

        return current_y

    def load_gng_logo(self, size: int) -> Image.Image:
        """Load and resize the actual GNG logo"""
        try:
            # Path to the actual GNG logo
            logo_path = "static/gng-logo.png"

            # Check if logo exists
            if os.path.exists(logo_path):
                # Load the actual logo
                logo_img = Image.open(logo_path).convert('RGBA')

                # Resize maintaining aspect ratio
                logo_img.thumbnail((size, size), Image.Resampling.LANCZOS)

                # Create a square canvas and center the logo
                final_logo = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                logo_w, logo_h = logo_img.size
                paste_x = (size - logo_w) // 2
                paste_y = (size - logo_h) // 2
                final_logo.paste(logo_img, (paste_x, paste_y), logo_img)

                return final_logo

            else:
                # Fallback to placeholder if logo not found
                return self.create_placeholder_logo(size)

        except Exception as e:
            logger.warning(f"Failed to load GNG logo: {e}, using placeholder")
            return self.create_placeholder_logo(size)

    def create_placeholder_logo(self, size: int) -> Image.Image:
        """Create a simple GNG logo placeholder as fallback"""
        logo_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        logo_draw = ImageDraw.Draw(logo_img)

        # Draw circular background
        circle_color = self.hex_to_rgb(ACCENT_GOLD)
        logo_draw.ellipse([0, 0, size-1, size-1], fill=circle_color, outline=circle_color)

        # Draw GNG text
        font_size = max(16, size // 4)
        try:
            logo_font = self.get_font(font_size, bold=True)
            text_color = self.hex_to_rgb(BACKGROUND_COLOR)

            # Center the text
            bbox = logo_draw.textbbox((0, 0), "GNG", font=logo_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (size - text_width) // 2
            text_y = (size - text_height) // 2

            logo_draw.text((text_x, text_y), "GNG", font=logo_font, fill=text_color)
        except Exception:
            # Fallback: just draw the circle
            pass

        return logo_img

    def generate_thumbnail(self, title: str, subtitle: str = None) -> str:
        """
        Generate a thumbnail image for the video
        """
        try:
            logger.info(f"Generating thumbnail for: {title}")

            # Create base image
            img = Image.new('RGB', (self.width, self.height), self.hex_to_rgb(BACKGROUND_COLOR))
            draw = ImageDraw.Draw(img)

            # Add subtle gradient effect
            self.add_gradient_overlay(img)

            # Position elements based on aspect ratio
            center_x = self.width // 2
            if self.video_mode == "shorts":
                # Vertical layout
                title_y = self.height // 3
                subtitle_y = self.height // 2 + 100
                logo_x = self.width - self.logo_size - 40
                logo_y = 40
            else:
                # Horizontal layout
                title_y = self.height // 2 - 50
                subtitle_y = self.height // 2 + 80
                logo_x = self.width - self.logo_size - 30
                logo_y = 30

            # Draw main title
            title_font = self.get_font(64 if self.video_mode == "standard" else 72, bold=True)
            max_title_width = self.width - 100
            self.draw_text_with_wrap(
                draw, title, center_x, title_y, title_font, ACCENT_GOLD, max_title_width
            )

            # Draw subtitle if provided
            if subtitle:
                subtitle_font = self.get_font(32 if self.video_mode == "standard" else 36)
                max_subtitle_width = self.width - 120
                self.draw_text_with_wrap(
                    draw, subtitle, center_x, subtitle_y, subtitle_font, TEXT_COLOR, max_subtitle_width
                )

            # Add GNG logo
            logo = self.load_gng_logo(self.logo_size)
            img.paste(logo, (logo_x, logo_y), logo)

            # Add decorative elements
            self.add_decorative_elements(draw)

            # Save thumbnail
            thumbnail_filename = f"thumb_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            thumbnail_dir = "static/thumbnails"
            os.makedirs(thumbnail_dir, exist_ok=True)

            thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

            # Save as high-quality JPEG
            img.save(thumbnail_path, 'JPEG', quality=92, optimize=True)

            logger.info(f"Thumbnail generated: {thumbnail_path}")
            return thumbnail_path

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise

    def add_gradient_overlay(self, img: Image.Image):
        """Add subtle gradient overlay to the background"""
        try:
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # Create subtle radial gradient effect
            center_x, center_y = self.width // 2, self.height // 2
            max_radius = max(self.width, self.height) // 2

            for i in range(max_radius, 0, -20):
                # Fade from center outward
                alpha = max(0, min(30, i // 20))
                color = (*self.hex_to_rgb(ACCENT_GOLD), alpha)

                # Draw ellipse for gradient effect
                left = center_x - i
                top = center_y - i
                right = center_x + i
                bottom = center_y + i

                if left < self.width and top < self.height and right > 0 and bottom > 0:
                    draw.ellipse([left, top, right, bottom], fill=color)

            # Blend with original image
            img.paste(overlay, (0, 0), overlay)

        except Exception as e:
            logger.warning(f"Failed to add gradient overlay: {e}")

    def add_decorative_elements(self, draw: ImageDraw.Draw):
        """Add decorative corner elements"""
        try:
            # Add corner accent lines
            accent_color = self.hex_to_rgb(ACCENT_GOLD)
            line_length = 80 if self.video_mode == "standard" else 100
            line_thickness = 4

            # Top left corner
            draw.rectangle([30, 30, 30 + line_length, 30 + line_thickness], fill=accent_color)
            draw.rectangle([30, 30, 30 + line_thickness, 30 + line_length], fill=accent_color)

            # Bottom right corner
            bottom_x = self.width - 30
            bottom_y = self.height - 30
            draw.rectangle([bottom_x - line_length, bottom_y - line_thickness, bottom_x, bottom_y], fill=accent_color)
            draw.rectangle([bottom_x - line_thickness, bottom_y - line_length, bottom_x, bottom_y], fill=accent_color)

        except Exception as e:
            logger.warning(f"Failed to add decorative elements: {e}")

# Async wrapper functions for integration
async def generate_video_thumbnail(title: str, video_mode: str = "standard", subtitle: str = None) -> str:
    """
    Generate thumbnail for video content
    """
    generator = ThumbnailGenerator(video_mode)

    try:
        # Create subtitle from video mode if not provided
        if not subtitle:
            if video_mode == "shorts":
                subtitle = "Quick insights • Optimized for mobile"
            else:
                subtitle = "Professional presentation • Good Neighbor Guard"

        thumbnail_path = generator.generate_thumbnail(title, subtitle)
        return thumbnail_path

    except Exception as e:
        logger.error(f"Video thumbnail generation failed: {e}")
        raise
    finally:
        generator.cleanup()

async def generate_phase3_thumbnail(title: str, video_mode: str = "standard") -> str:
    """
    Generate thumbnail specifically for Phase 3 videos
    """
    generator = ThumbnailGenerator(video_mode)

    try:
        subtitle = "Auto-enhanced with AI narration • GNG Phase 3"
        thumbnail_path = generator.generate_thumbnail(title, subtitle)
        return thumbnail_path

    except Exception as e:
        logger.error(f"Phase 3 thumbnail generation failed: {e}")
        raise
    finally:
        generator.cleanup()