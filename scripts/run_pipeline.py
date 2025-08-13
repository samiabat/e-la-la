#!/usr/bin/env python3
import os
import sys

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import click
from src.pipeline import run_pipeline, run_pipeline_multi

@click.command()
@click.option('--input', 'input_path', type=str, default=None, help='Local input video path')
@click.option('--profile', type=str, default='tiktok')
@click.option('--config', 'config_path', type=str, default='configs/pipeline.yaml')
@click.option('--duration', type=float, default=None, help='Override target duration (sec)')
@click.option('--query', 'yt_query', type=str, default=None, help='Creative Commons YouTube search query')
@click.option('--no-subtitles', is_flag=True, help='Disable subtitle burn-in')
@click.option('--multi', is_flag=True, help='Generate multiple clips (variable durations)')
@click.option('--max-clips', type=int, default=3, help='Max clips to generate in multi mode')
@click.option('--durations', type=str, default=None, help='Comma-separated durations in seconds, e.g. 20,30,45,60')
@click.option('--stride', type=float, default=1.0, help='Stride seconds for window scan')
@click.option('--tail-pad', type=float, default=1.5, help='Seconds to pad after detected end (0..3s)')
@click.option('--head-pad', type=float, default=1.5, help='Seconds to include before the detected start (0..3s)')
@click.option('--min-dur', type=float, default=20.0, help='Minimum duration bound for idea-aware end (seconds)')
@click.option('--max-dur', type=float, default=120.0, help='Maximum duration bound for idea-aware end (seconds)')
@click.option('--audio-only', is_flag=True, help='Export audio files (mp3) instead of video')
def main(input_path, profile, config_path, duration, yt_query, no_subtitles, multi, max_clips, durations, stride, tail_pad, head_pad, min_dur, max_dur, audio_only):
    subs_override = False if no_subtitles else None
    if multi:
        dur_list = None
        if durations:
            try:
                dur_list = [float(x.strip()) for x in durations.split(',') if x.strip()]
            except Exception:
                raise click.ClickException('Invalid --durations format; use comma-separated seconds, e.g. 20,30,45,60')
        paths = run_pipeline_multi(
            input_path=input_path,
            profile=profile,
            config_path=config_path,
            via_youtube_query=yt_query,
            durations=dur_list,
            max_clips=max_clips,
            stride_sec=stride,
            subs_enabled_override=subs_override,
            idea_end=True,
            min_dur=min_dur,
            max_dur=max_dur,
            tail_pad_sec=tail_pad,
            head_pad_sec=head_pad,
            export_audio_only=audio_only,
        )
        for p in paths:
            click.echo(p)
    else:
        path = run_pipeline(
            input_path=input_path,
            profile=profile,
            config_path=config_path,
            via_youtube_query=yt_query,
            duration_override=duration,
            subs_enabled_override=subs_override,
            idea_end=True,
            min_dur=min_dur,
            max_dur=max_dur,
            tail_pad_sec=tail_pad,
            head_pad_sec=head_pad,
            export_audio_only=audio_only,
        )
        click.echo(path)

if __name__ == '__main__':
    main()
