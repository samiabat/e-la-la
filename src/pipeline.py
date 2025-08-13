import os
import yaml
from dataclasses import dataclass
from typing import Optional, List

from src.ingest.fetch_video import get_latest_cc_viral_video, download_cc_video
from src.analysis.engagement import best_window, top_windows_multi
from src.analysis.semantic import transcribe_with_words, detect_silences, pick_idea_endpoint
from src.edit.formatters import cut_segment, to_vertical, export_audio
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
    padding_color: str


def load_config(path: str, profile: str) -> PipelineConfig:
    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)
    p = cfg['profiles'][profile]
    return PipelineConfig(
        width=int(p['width']),
        height=int(p['height']),
        fps=int(p['fps']),
        duration=float(p['target_duration_sec']),
        blur=int(p.get('background_blur', 25)),
        subs_enabled=bool(cfg.get('subtitles', {}).get('enabled', True)),
        subs_model=str(cfg.get('subtitles', {}).get('model', 'tiny')),
        padding_color=str(p.get('padding_color', '#000000')),
    )


def run_pipeline(
    input_path: Optional[str],
    profile: str = 'tiktok',
    config_path: str = 'configs/pipeline.yaml',
    via_youtube_query: Optional[str] = None,
    duration_override: Optional[float] = None,
    subs_enabled_override: Optional[bool] = None,
    idea_end: bool = True,
    min_dur: float = 20.0,
    max_dur: float = 120.0,
    tail_pad_sec: float = 1.5,
    head_pad_sec: float = 0.0,
    export_audio_only: bool = False,
) -> str:
    """Produce a single final short and return its output path."""
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

    # Find an engaging start
    score_win = min((duration_override or conf.duration or 30), 30)
    start, _ = best_window(input_path, window_sec=score_win, stride_sec=1.0)

    os.makedirs('data/working', exist_ok=True)
    seg_path = os.path.join('data/working', 'segment.mp4')

    # Probe media duration once
    try:
        import ffmpeg as _ff
        meta = _ff.probe(input_path)
        fmt = meta.get('format', {})
        media_dur = float(fmt.get('duration', 0.0)) if fmt.get('duration') else 0.0
    except Exception:
        media_dur = 0.0

    if idea_end:
        # Idea-aware end selection
        try:
            transcript = transcribe_with_words(input_path, model=conf.subs_model)
        except Exception:
            transcript = None
        try:
            sils = detect_silences(input_path)
        except Exception:
            sils = []
        end = pick_idea_endpoint(transcript, sils, start_hint=start, min_dur=float(min_dur), max_dur=float(max_dur))
        end += max(0.0, min(3.0, float(tail_pad_sec)))
        if media_dur and end > media_dur:
            end = media_dur
        head = max(0.0, min(3.0, float(head_pad_sec)))
        out_start = max(0.0, start - head)
        duration = max(0.1, end - start + head)
        if media_dur:
            duration = min(duration, max(0.1, media_dur - out_start))
        cut_segment(input_path, seg_path, start=out_start, duration=duration)
    else:
        base_dur = float(duration_override or conf.duration)
        head = max(0.0, min(3.0, float(head_pad_sec)))
        out_start = max(0.0, start - head)
        duration = base_dur + head
        if media_dur:
            duration = min(duration, max(0.1, media_dur - out_start))
        cut_segment(input_path, seg_path, start=out_start, duration=duration)

    if export_audio_only:
        final_audio = os.path.join('data/outputs/shorts', 'short_final.mp3')
        os.makedirs(os.path.dirname(final_audio), exist_ok=True)
        export_audio(seg_path, final_audio)
        return final_audio

    vert_path = os.path.join('data/working', 'vertical.mp4')
    to_vertical(seg_path, vert_path, width=conf.width, height=conf.height, blur=conf.blur, padding_color=conf.padding_color)

    final_path = os.path.join('data/outputs/shorts', 'short_final.mp4')
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    if conf.subs_enabled:
        burn_subtitles_karaoke(vert_path, final_path, model=conf.subs_model)
    else:
        import ffmpeg
        ffmpeg.input(vert_path).output(final_path, c='copy', movflags='faststart').overwrite_output().run(quiet=True)

    return final_path


def run_pipeline_multi(
    input_path: Optional[str],
    profile: str = 'tiktok',
    config_path: str = 'configs/pipeline.yaml',
    via_youtube_query: Optional[str] = None,
    durations: Optional[List[float]] = None,
    max_clips: int = 3,
    stride_sec: float = 1.0,
    subs_enabled_override: Optional[bool] = None,
    idea_end: bool = False,
    min_dur: float = 20.0,
    max_dur: float = 120.0,
    tail_pad_sec: float = 1.5,
    head_pad_sec: float = 0.0,
    export_audio_only: bool = False,
) -> List[str]:
    """Generate multiple clips (variable length) and return list of final paths."""
    conf = load_config(config_path, profile)
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

    durations = durations or [20, 30, 45, 60]
    windows = top_windows_multi(input_path, durations=durations, stride_sec=stride_sec, max_clips=max_clips)

    # Probe media duration once and compute transcript/silences once
    try:
        import ffmpeg as _ff
        meta = _ff.probe(input_path)
        fmt = meta.get('format', {})
        media_dur = float(fmt.get('duration', 0.0)) if fmt.get('duration') else 0.0
    except Exception:
        media_dur = 0.0

    transcript = None
    sils: List = []
    if idea_end:
        try:
            transcript = transcribe_with_words(input_path, model=conf.subs_model)
        except Exception:
            transcript = None
        try:
            sils = detect_silences(input_path)
        except Exception:
            sils = []

    out_paths: List[str] = []
    os.makedirs('data/working', exist_ok=True)
    os.makedirs('data/outputs/shorts', exist_ok=True)

    for idx, (start, dur, _score) in enumerate(windows, start=1):
        head = max(0.0, min(3.0, float(head_pad_sec)))
        out_start = max(0.0, start - head)

        if idea_end:
            end = pick_idea_endpoint(transcript, sils, start_hint=start, min_dur=float(min_dur), max_dur=float(max_dur))
            end += max(0.0, min(3.0, float(tail_pad_sec)))
            if media_dur and end > media_dur:
                end = media_dur
            duration = max(0.1, end - start + head)
        else:
            duration = float(dur) + head

        if media_dur:
            duration = min(duration, max(0.1, media_dur - out_start))

        seg_path = os.path.join('data/working', f'segment_{idx}.mp4')
        cut_segment(input_path, seg_path, start=out_start, duration=duration)

        if export_audio_only:
            final_audio = os.path.join('data/outputs/shorts', f'short_final_{idx}.mp3')
            export_audio(seg_path, final_audio)
            out_paths.append(final_audio)
            continue

        vert_path = os.path.join('data/working', f'vertical_{idx}.mp4')
        to_vertical(seg_path, vert_path, width=conf.width, height=conf.height, blur=conf.blur, padding_color=conf.padding_color)

        final_path = os.path.join('data/outputs/shorts', f'short_final_{idx}.mp4')
        if conf.subs_enabled:
            burn_subtitles_karaoke(vert_path, final_path, model=conf.subs_model)
        else:
            import ffmpeg
            ffmpeg.input(vert_path).output(final_path, c='copy', movflags='faststart').overwrite_output().run(quiet=True)
        out_paths.append(final_path)

    return out_paths
