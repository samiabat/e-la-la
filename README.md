# e-la-la

Automated short-form content pipeline (legal-compliant): analyze a source video you own (or CC-licensed), find the most engaging segment, crop to vertical, and add basic styled subtitles for TikTok/Shorts.

Important: Do not download or reuse copyrighted videos without permission. This repo only processes local files or Creative Commons videos you have the right to use.

## Quick start

1) Prereqs (macOS):

```zsh
brew install ffmpeg yt-dlp
```

Then install Python deps (Python 3.10+ recommended):

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Place a source video you own (or with a CC license) into `data/raw/`.

3) Run the pipeline to produce a TikTok-ready clip (defaults to 1080x1920, ~20s):

```zsh
python scripts/run_pipeline.py --input data/raw/your_video.mp4 --profile tiktok --duration 20
```

Outputs will be written to `data/outputs/shorts/`.

## Legal note about YouTube

- This project does not download or republish copyrighted content. If you use the optional YouTube metadata + download helper, it enforces Creative Commons license checks and will refuse otherwise (requires `yt-dlp`).
- For your own uploads or licensed content, you may point the pipeline at a local file path.

## Folder structure

```
configs/
	pipeline.yaml        # Settings: output profiles, durations, style options
data/
	raw/                 # Source videos you own or are licensed to use
	working/             # Temp work area
	outputs/
		shorts/            # Final TikTok/Shorts exports
src/
	analysis/
		engagement.py      # Finds highest-energy/scene activity segments
	edit/
		formatters.py      # 9:16 vertical formatting and background blur
		subtitles.py       # Whisper-based transcript + simple styled burn-in
	ingest/
		youtube_meta.py    # YouTube Data API metadata + CC license checks
		fetch_video.py     # Optional downloader (CC-only); otherwise local files
	pipeline.py          # Orchestrates: ingest -> analyze -> edit -> export
scripts/
	run_pipeline.py      # CLI wrapper for src.pipeline
```

## Notes

- Subtitles use Whisper (tiny) by default; first run will download a small model. You can skip subtitles with `--no-subtitles`.
- Engagement heuristic uses audio energy + scene activity. You can tweak weights in `configs/pipeline.yaml`.
- Uploading to TikTok/YouTube is not automated here; export files are ready for manual upload or your own uploader.

