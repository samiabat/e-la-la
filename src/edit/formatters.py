from typing import Tuple, Optional
import ffmpeg
import os
import tempfile
import subprocess
import json

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def detect_content_region(input_path: str, target_aspect: float = 9/16) -> Optional[Tuple[int, int, int, int]]:
    """
    Detect the best crop region using face detection and content analysis.
    Returns (x, y, width, height) or None if detection fails.
    """
    if not HAS_OPENCV:
        return None
    
    try:
        # Use ffprobe to get video info
        probe = ffmpeg.probe(input_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        width = int(video_info['width'])
        height = int(video_info['height'])
        
        # Extract a few frames for analysis
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_frame:
            # Extract frame at 25% duration
            duration = float(video_info.get('duration', 0))
            timestamp = duration * 0.25 if duration > 0 else 2.0
            
            (
                ffmpeg
                .input(input_path, ss=timestamp)
                .output(tmp_frame.name, vframes=1)
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Load frame and detect faces
            frame = cv2.imread(tmp_frame.name)
            if frame is None:
                os.unlink(tmp_frame.name)
                return None
                
            # Use OpenCV's face detector
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            os.unlink(tmp_frame.name)
            
            if len(faces) > 0:
                # Find the center of all detected faces
                face_centers_x = []
                face_centers_y = []
                for (x, y, w, h) in faces:
                    face_centers_x.append(x + w // 2)
                    face_centers_y.append(y + h // 2)
                
                avg_face_x = sum(face_centers_x) // len(face_centers_x)
                avg_face_y = sum(face_centers_y) // len(face_centers_y)
                
                # Calculate crop dimensions for target aspect ratio
                target_width = int(height * target_aspect)
                target_height = height
                
                if target_width > width:
                    # Need to crop vertically instead
                    target_width = width
                    target_height = int(width / target_aspect)
                    
                    # Center crop around face Y position
                    crop_y = max(0, min(height - target_height, avg_face_y - target_height // 2))
                    return (0, crop_y, target_width, target_height)
                else:
                    # Crop horizontally, center around face X position
                    crop_x = max(0, min(width - target_width, avg_face_x - target_width // 2))
                    return (crop_x, 0, target_width, target_height)
            
    except Exception:
        pass
    
    return None


def to_vertical(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    blur: int = 18,
    padding_color: str = 'black',
    fg_scale: float = 0.95,  # scale foreground height relative to canvas (e.g., 0.95 = 95%)
    bg_brightness: float = 0.08,  # lift background brightness slightly
    bg_saturation: float = 1.05,  # a touch more color on BG
):
    """
    Convert any aspect to an exact WxH canvas (e.g., 1080x1920) by:
    - making a blurred background that fills the canvas
    - scaling the foreground to fit and padding to center
    - using content-aware cropping when possible to follow subjects
    Ensures the final output dimensions are exactly width x height.
    """
    # For now, disable content-aware cropping due to FFmpeg-python limitations
    # TODO: Re-enable when we can resolve the split filter issue
    crop_region = None
    
    if crop_region:
        # Use detected crop region with duplicated inputs to avoid split complexity
        crop_x, crop_y, crop_w, crop_h = crop_region
        
        # Background: crop and scale to fill canvas, blur (using separate input)
        bg = (
            ffmpeg
            .input(input_path)
            .video
            .filter('crop', crop_w, crop_h, crop_x, crop_y)
            .filter('scale', width, height, force_original_aspect_ratio='increase')
            .filter('crop', width, height)
            .filter('boxblur', blur)
            .filter('eq', brightness=bg_brightness, saturation=bg_saturation)
        )
        
        # Foreground: crop and scale to fit canvas exactly (using separate input) 
        fg = (
            ffmpeg
            .input(input_path)
            .video
            .filter('crop', crop_w, crop_h, crop_x, crop_y)
            .filter('scale', width, height)
        )
        
        # Overlay foreground on background
        video = ffmpeg.overlay(bg, fg, x=0, y=0).filter('format', 'yuv420p')
        
        # Audio from original source (separate input)
        audio = ffmpeg.input(input_path).audio
        
    else:
        # Fallback to original logic
        # Background: fill, crop, blur, and gently brighten to exact canvas
        bg = (
            ffmpeg
            .input(input_path)
            .video
            .filter('scale', width, height, force_original_aspect_ratio='increase')
            .filter('crop', width, height)
            .filter('boxblur', blur)
            .filter('eq', brightness=bg_brightness, saturation=bg_saturation)
        )

        # Foreground: target a fraction of canvas HEIGHT (keeps aspect ratio), centered
        # Note: Scaling by height avoids the "too small" look on wide 16:9 sources.
        fg = (
            ffmpeg
            .input(input_path)
            .video
            .filter('scale', -2, int(height * fg_scale))
        )

        video = ffmpeg.overlay(bg, fg, x='(W-w)/2', y='(H-h)/2').filter('format', 'yuv420p')
        
        a_inp = ffmpeg.input(input_path)
        audio = a_inp.audio

    (
        ffmpeg
        .output(video, audio, output_path, r=30, preset='veryfast', crf=20, movflags='faststart')
        .overwrite_output()
        .run(quiet=True)
    )


def cut_segment(input_path: str, output_path: str, start: float, duration: float):
    (
        ffmpeg
        .input(input_path, ss=start, t=duration)
        .output(output_path, c='copy', movflags='faststart')
        .overwrite_output()
        .run(quiet=True)
    )


def export_audio(input_path: str, output_path: str, bitrate: str = '192k'):
    """Extract audio to MP3 (or extension-driven format)."""
    a = ffmpeg.input(input_path).audio
    # If extension is .mp3, use libmp3lame; else let ffmpeg pick
    kwargs = {}
    if output_path.lower().endswith('.mp3'):
        kwargs.update({'acodec': 'libmp3lame', 'audio_bitrate': bitrate})
    (
        ffmpeg
        .output(a, output_path, **kwargs)
        .overwrite_output()
        .run(quiet=True)
    )
