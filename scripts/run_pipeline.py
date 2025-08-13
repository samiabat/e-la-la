#!/usr/bin/env python3
import click
from src.pipeline import run_pipeline

@click.command()
@click.option('--input', 'input_path', type=str, default=None, help='Local input video path')
@click.option('--profile', type=str, default='tiktok')
@click.option('--config', 'config_path', type=str, default='configs/pipeline.yaml')
@click.option('--duration', type=float, default=None, help='Override target duration (sec)')
@click.option('--query', 'yt_query', type=str, default=None, help='Creative Commons YouTube search query')
@click.option('--no-subtitles', is_flag=True, help='Disable subtitle burn-in')
def main(input_path, profile, config_path, duration, yt_query, no_subtitles):
    path = run_pipeline(
        input_path=input_path,
        profile=profile,
        config_path=config_path,
        via_youtube_query=yt_query,
        duration_override=duration,
        subs_enabled_override=False if no_subtitles else None,
    )
    click.echo(path)

if __name__ == '__main__':
    main()
