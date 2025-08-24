"""
Rich video editing effects for creating dynamic, engaging TikTok content.
Includes people detection, dynamic zooms, split screens, and creative transitions.
"""

from typing import List, Tuple, Dict, Optional
import ffmpeg
import cv2
import numpy as np
import os
import tempfile
from dataclasses import dataclass


@dataclass
class PersonSegment:
    """Represents a segment where people are detected."""
    start_sec: float
    end_sec: float
    person_count: int
    confidence: float


@dataclass
class EffectSegment:
    """Represents a specific effect to apply to a video segment."""
    start_sec: float
    end_sec: float
    effect_type: str  # 'zoom_in', 'zoom_out', 'split_screen', 'full_frame', 'pan_left', 'pan_right'
    params: Dict


def detect_people_segments(
    input_path: str,
    sample_interval: float = 2.0,
    confidence_threshold: float = 0.5
) -> List[PersonSegment]:
    """
    Detect segments where people appear in the video using OpenCV's HOG detector.
    
    Args:
        input_path: Path to input video
        sample_interval: Seconds between samples for analysis
        confidence_threshold: Minimum confidence for person detection
    
    Returns:
        List of PersonSegment objects
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return []
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    # Initialize HOG descriptor for person detection
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    
    segments = []
    current_segment = None
    
    # Sample frames at intervals
    sample_frames = int(sample_interval * fps)
    
    for frame_idx in range(0, total_frames, sample_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            break
            
        # Resize frame for faster processing
        height, width = frame.shape[:2]
        scale = min(640 / width, 480 / height)
        new_width, new_height = int(width * scale), int(height * scale)
        resized = cv2.resize(frame, (new_width, new_height))
        
        # Detect people
        boxes, weights = hog.detectMultiScale(
            resized,
            winStride=(8, 8),
            padding=(32, 32),
            scale=1.05
        )
        
        current_time = frame_idx / fps
        person_count = len([w for w in weights if w > confidence_threshold])
        
        if person_count > 0:
            if current_segment is None:
                # Start new segment
                current_segment = PersonSegment(
                    start_sec=current_time,
                    end_sec=current_time,
                    person_count=person_count,
                    confidence=max(weights) if weights.size > 0 else 0.0
                )
            else:
                # Extend current segment
                current_segment.end_sec = current_time
                current_segment.person_count = max(current_segment.person_count, person_count)
                current_segment.confidence = max(current_segment.confidence, max(weights) if weights.size > 0 else 0.0)
        else:
            if current_segment is not None:
                # End current segment
                segments.append(current_segment)
                current_segment = None
    
    # Add final segment if exists
    if current_segment is not None:
        segments.append(current_segment)
    
    cap.release()
    return segments


def plan_rich_effects(
    input_path: str,
    duration: float,
    person_segments: List[PersonSegment]
) -> List[EffectSegment]:
    """
    Plan a sequence of rich effects based on detected people and video characteristics.
    
    Args:
        input_path: Path to input video
        duration: Total duration of the video
        person_segments: List of detected person segments
    
    Returns:
        List of EffectSegment objects describing the editing plan
    """
    effects = []
    
    # Sort person segments by start time
    person_segments.sort(key=lambda x: x.start_sec)
    
    # Default effect for segments without people
    current_time = 0.0
    
    for segment in person_segments:
        # Add transition effect before person segment if there's a gap
        if segment.start_sec > current_time + 1.0:
            effects.append(EffectSegment(
                start_sec=current_time,
                end_sec=segment.start_sec,
                effect_type='full_frame',
                params={'transition': 'fade'}
            ))
        
        # Determine effect based on person count
        segment_duration = segment.end_sec - segment.start_sec
        
        if segment.person_count >= 2 and segment_duration > 8.0:
            # Long multi-person segment: use split screen
            mid_point = segment.start_sec + segment_duration / 2
            
            # First half: zoom in on one person
            effects.append(EffectSegment(
                start_sec=segment.start_sec,
                end_sec=mid_point,
                effect_type='zoom_in',
                params={'target_scale': 1.5, 'focus': 'left'}
            ))
            
            # Second half: split screen
            effects.append(EffectSegment(
                start_sec=mid_point,
                end_sec=segment.end_sec,
                effect_type='split_screen',
                params={'orientation': 'horizontal'}
            ))
            
        elif segment.person_count >= 2:
            # Short multi-person segment: quick zoom transitions
            effects.append(EffectSegment(
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                effect_type='zoom_in',
                params={'target_scale': 1.3, 'focus': 'center'}
            ))
            
        elif segment.person_count == 1 and segment_duration > 5.0:
            # Single person: dynamic zoom with panning
            mid_point = segment.start_sec + segment_duration / 2
            
            effects.append(EffectSegment(
                start_sec=segment.start_sec,
                end_sec=mid_point,
                effect_type='zoom_in',
                params={'target_scale': 1.4, 'focus': 'center'}
            ))
            
            effects.append(EffectSegment(
                start_sec=mid_point,
                end_sec=segment.end_sec,
                effect_type='pan_left',
                params={'zoom_scale': 1.2}
            ))
            
        else:
            # Default: subtle zoom
            effects.append(EffectSegment(
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                effect_type='zoom_in',
                params={'target_scale': 1.2, 'focus': 'center'}
            ))
        
        current_time = segment.end_sec
    
    # Add final effect if needed
    if current_time < duration:
        effects.append(EffectSegment(
            start_sec=current_time,
            end_sec=duration,
            effect_type='full_frame',
            params={'transition': 'fade'}
        ))
    
    return effects


def apply_rich_edits(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    blur: int = 18,
    padding_color: str = 'black',
    bg_brightness: float = 0.08,
    bg_saturation: float = 1.05,
) -> None:
    """
    Apply rich editing effects to create dynamic, engaging vertical video.
    
    Args:
        input_path: Path to input video
        output_path: Path for output video
        width: Target width (default 1080 for TikTok)
        height: Target height (default 1920 for TikTok)
        blur: Background blur amount
        padding_color: Background padding color
        bg_brightness: Background brightness adjustment
        bg_saturation: Background saturation adjustment
    """
    # Get video duration
    try:
        probe = ffmpeg.probe(input_path)
        duration = float(probe['format']['duration'])
    except Exception:
        duration = 30.0  # fallback
    
    # Detect people in the video
    person_segments = detect_people_segments(input_path)
    
    # Plan effects based on detected segments
    effect_segments = plan_rich_effects(input_path, duration, person_segments)
    
    # Create temporary files for each effect segment
    temp_segments = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        for i, effect in enumerate(effect_segments):
            temp_file = os.path.join(temp_dir, f'segment_{i}.mp4')
            
            # Apply the specific effect
            _apply_single_effect(
                input_path, temp_file, effect,
                width, height, blur, padding_color,
                bg_brightness, bg_saturation
            )
            
            temp_segments.append(temp_file)
        
        # Concatenate all segments
        if temp_segments:
            _concatenate_segments(temp_segments, output_path)
        else:
            # Fallback to basic conversion
            from .formatters import to_vertical
            to_vertical(input_path, output_path, width, height, blur, padding_color)
            
    finally:
        # Cleanup temporary files
        for temp_file in temp_segments:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        try:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        except:
            pass


def _apply_single_effect(
    input_path: str,
    output_path: str,
    effect: EffectSegment,
    width: int,
    height: int,
    blur: int,
    padding_color: str,
    bg_brightness: float,
    bg_saturation: float
) -> None:
    """Apply a single effect to a video segment."""
    
    # Extract the segment first
    segment_input = ffmpeg.input(
        input_path,
        ss=effect.start_sec,
        t=effect.end_sec - effect.start_sec
    )
    
    # Create background (same as original to_vertical)
    bg = (
        segment_input
        .video
        .filter('scale', width, height, force_original_aspect_ratio='increase')
        .filter('crop', width, height)
        .filter('boxblur', blur)
        .filter('eq', brightness=bg_brightness, saturation=bg_saturation)
    )
    
    # Apply specific effect to foreground
    if effect.effect_type == 'zoom_in':
        fg = _create_zoom_effect(segment_input, effect, width, height)
    elif effect.effect_type == 'zoom_out':
        fg = _create_zoom_out_effect(segment_input, effect, width, height)
    elif effect.effect_type == 'split_screen':
        fg = _create_split_screen_effect(segment_input, effect, width, height)
    elif effect.effect_type == 'pan_left':
        fg = _create_pan_effect(segment_input, effect, width, height, 'left')
    elif effect.effect_type == 'pan_right':
        fg = _create_pan_effect(segment_input, effect, width, height, 'right')
    else:  # full_frame
        fg = (
            segment_input
            .video
            .filter('scale', -2, int(height * 0.95))
        )
    
    # Combine background and foreground
    video = ffmpeg.overlay(bg, fg, x='(W-w)/2', y='(H-h)/2').filter('format', 'yuv420p')
    
    # Check if input has audio streams
    try:
        probe = ffmpeg.probe(input_path)
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    except:
        has_audio = False
    
    if has_audio:
        # Use existing audio
        audio = segment_input.audio
        output_stream = ffmpeg.output(video, audio, output_path, vcodec='libx264', acodec='aac', r=30, preset='veryfast', crf=20, movflags='faststart')
    else:
        # Video only output
        output_stream = ffmpeg.output(video, output_path, vcodec='libx264', r=30, preset='veryfast', crf=20, movflags='faststart')
    
    # Output
    output_stream.overwrite_output().run(quiet=False)


def _create_zoom_effect(input_stream, effect: EffectSegment, width: int, height: int):
    """Create a dynamic zoom-in effect."""
    target_scale = effect.params.get('target_scale', 1.3)
    focus = effect.params.get('focus', 'center')
    
    if focus == 'left':
        # Zoom and pan to focus on left side
        return (
            input_stream
            .video
            .filter('scale', int(width * target_scale), -2)
            .filter('crop', width, int(height * 0.95), 0, '(ih-oh)/2')
        )
    elif focus == 'right':
        # Zoom and pan to focus on right side  
        return (
            input_stream
            .video
            .filter('scale', int(width * target_scale), -2)
            .filter('crop', width, int(height * 0.95), f'iw-{width}', '(ih-oh)/2')
        )
    else:  # center
        # Simple center zoom
        return (
            input_stream
            .video
            .filter('scale', -2, int(height * target_scale * 0.95))
            .filter('crop', width, int(height * 0.95), '(iw-ow)/2', '(ih-oh)/2')
        )


def _create_zoom_out_effect(input_stream, effect: EffectSegment, width: int, height: int):
    """Create a zoom-out effect."""
    return (
        input_stream
        .video
        .filter('scale', -2, int(height * 0.8))
    )


def _create_split_screen_effect(input_stream, effect: EffectSegment, width: int, height: int):
    """Create a split-screen effect for multi-person segments."""
    orientation = effect.params.get('orientation', 'horizontal')
    
    if orientation == 'horizontal':
        # Top and bottom split
        top_half = (
            input_stream
            .video
            .filter('crop', 'iw', 'ih/2', 0, 0)
            .filter('scale', width, height // 2)
        )
        
        bottom_half = (
            input_stream
            .video
            .filter('crop', 'iw', 'ih/2', 0, 'ih/2')
            .filter('scale', width, height // 2)
        )
        
        # Combine vertically
        return ffmpeg.filter([top_half, bottom_half], 'vstack')
    else:
        # Left and right split (vertical split) - simpler approach
        return (
            input_stream
            .video
            .filter('scale', -2, int(height * 0.95))
        )


def _create_pan_effect(input_stream, effect: EffectSegment, width: int, height: int, direction: str):
    """Create a panning effect."""
    zoom_scale = effect.params.get('zoom_scale', 1.2)
    
    # Create zoomed version with safer calculations
    target_height = int(height * 0.95)
    
    if direction == 'left':
        # Pan from right to left (simpler version)
        return (
            input_stream
            .video
            .filter('scale', int(width * zoom_scale), -2)
            .filter('crop', width, target_height, f'(iw-{width})*0.8', '(ih-oh)/2')
        )
    else:  # right
        # Pan from left to right (simpler version)
        return (
            input_stream
            .video
            .filter('scale', int(width * zoom_scale), -2)
            .filter('crop', width, target_height, f'(iw-{width})*0.2', '(ih-oh)/2')
        )


def _concatenate_segments(segment_paths: List[str], output_path: str) -> None:
    """Concatenate multiple video segments into final output."""
    if not segment_paths:
        return
    
    if len(segment_paths) == 1:
        # Just copy single segment
        (
            ffmpeg
            .input(segment_paths[0])
            .output(output_path, c='copy', movflags='faststart')
            .overwrite_output()
            .run(quiet=True)
        )
        return
    
    # Create inputs for all segments
    inputs = [ffmpeg.input(path) for path in segment_paths]
    
    # Check if the first segment has audio
    try:
        probe = ffmpeg.probe(segment_paths[0])
        has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    except:
        has_audio = False
    
    # Concatenate all segments
    if has_audio:
        (
            ffmpeg
            .concat(*inputs, v=1, a=1)
            .output(output_path, r=30, preset='veryfast', crf=20, movflags='faststart')
            .overwrite_output()
            .run(quiet=True)
        )
    else:
        # Video only concatenation
        (
            ffmpeg
            .concat(*inputs, v=1, a=0)
            .output(output_path, r=30, preset='veryfast', crf=20, movflags='faststart')
            .overwrite_output()
            .run(quiet=True)
        )