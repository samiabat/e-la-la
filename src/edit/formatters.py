from typing import Tuple
import ffmpeg
import os


def to_vertical(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    blur: int = 25,
    padding_color: str = 'black',
):
    """
    Convert any aspect to an exact WxH canvas (e.g., 1080x1920) by:
    - making a blurred background that fills the canvas
    - scaling the foreground to fit and padding to center
    Ensures the final output dimensions are exactly width x height.
    """
    # Background: fill, crop, and blur to exact canvas
    bg = (
        ffmpeg
        .input(input_path)
        .video
        .filter('scale', width, height, force_original_aspect_ratio='increase')
        .filter('crop', width, height)
        .filter('boxblur', blur)
    )

    # Foreground: fit within canvas, pad to center with chosen color
    fg = (
        ffmpeg
        .input(input_path)
        .video
        .filter('scale', width, height, force_original_aspect_ratio='decrease')
        .filter('pad', width, height, '(ow-iw)/2', '(oh-ih)/2', color=padding_color)
    )

    video = ffmpeg.overlay(bg, fg, x=0, y=0).filter('format', 'yuv420p')
    audio = ffmpeg.input(input_path).audio

    ffmpeg.output(
        video, audio, output_path,
        r=30, preset='veryfast', crf=20, movflags='faststart'
    ).overwrite_output().run(quiet=True)


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
