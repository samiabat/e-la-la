from typing import Tuple
import ffmpeg
import os


def to_vertical(input_path: str, output_path: str, width: int = 1080, height: int = 1920, blur: int = 25):
    """
    Convert any aspect to 9:16 by letterboxing with blurred background.
    """
    probe = ffmpeg.probe(input_path)
    v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    src_w, src_h = int(v['width']), int(v['height'])

    stream = ffmpeg.input(input_path)
    # background: scale to fill and blur
    bg = stream.video.filter('scale', width, -1).filter('boxblur', blur)
    # foreground: scale to fit within
    fg = stream.video.filter('scale', -2, height).filter('crop', width, height)
    video = ffmpeg.overlay(bg, fg, x='(W-w)/2', y='(H-h)/2').filter('format', 'yuv420p')
    audio = stream.audio

    ffmpeg.output(video, audio, output_path, r=30, preset='veryfast', crf=20, movflags='faststart').overwrite_output().run(quiet=True)


def cut_segment(input_path: str, output_path: str, start: float, duration: float):
    (
        ffmpeg
        .input(input_path, ss=start, t=duration)
        .output(output_path, c='copy', movflags='faststart')
        .overwrite_output()
        .run(quiet=True)
    )
