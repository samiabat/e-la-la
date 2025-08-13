import os
import yaml
from dataclasses import dataclass
from typing import Optional

from src.ingest.fetch_video import get_latest_cc_viral_video, download_cc_video
from src.analysis.engagement import best_window
from src.edit.formatters import cut_segment, to_vertical
from src.edit.subtitles import burn_subtitles_karaoke


@dataclass
class PipelineConfig:
    width: int
    height: int
    fps: int
    duration: float
    blur: int
    subs_enabled: bool
    subs_model: str


def load_config(path: str, profile: str):
    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)
    p = cfg['profiles'][profile]
    return PipelineConfig(
        width=int(p['width']),
        height=int(p['height']),
        fps=int(p['fps']),
        duration=float(p['target_duration_sec']),
        blur=int(p.get('background_blur', 25)),
        subs_enabled=bool(cfg['subtitles'].get('enabled', True)),
        subs_model=str(cfg['subtitles'].get('model', 'tiny')),
    )


def run_pipeline(
    input_path: Optional[str],
    profile: str = 'tiktok',
    config_path: str = 'configs/pipeline.yaml',
    via_youtube_query: Optional[str] = None,
    duration_override: Optional[float] = None,
    subs_enabled_override: Optional[bool] = None,
) -> str:
    """
    Returns path to final exported short.
    """
    conf = load_config(config_path, profile)
    if duration_override is not None and duration_override > 0:
        conf.duration = float(duration_override)
    if subs_enabled_override is not None:
        conf.subs_enabled = bool(subs_enabled_override)

    if via_youtube_query and not input_path:
        item = get_latest_cc_viral_video(via_youtube_query)
        if not item:
            raise RuntimeError('No CC-licensed video found for query')
        input_path = download_cc_video(item.url, 'data/raw')
        if not input_path:
            raise RuntimeError('Failed to download CC video')

    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError('Input video not found')

    # 1) pick engaging window
    start, _score = best_window(input_path, window_sec=conf.duration, stride_sec=1.0)

    # 2) cut segment
    os.makedirs('data/working', exist_ok=True)
    seg_path = os.path.join('data/working', 'segment.mp4')
    cut_segment(input_path, seg_path, start=start, duration=conf.duration)

    # 3) verticalize
    vert_path = os.path.join('data/working', 'vertical.mp4')
    to_vertical(seg_path, vert_path, width=conf.width, height=conf.height, blur=conf.blur)

    # 4) subtitles
    final_path = os.path.join('data/outputs/shorts', 'short_final.mp4')
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    if conf.subs_enabled:
        burn_subtitles_karaoke(vert_path, final_path, model=conf.subs_model)
    else:
        # pass-through
        import ffmpeg
        ffmpeg.input(vert_path).output(final_path, c='copy', movflags='faststart').overwrite_output().run(quiet=True)

    return final_path
