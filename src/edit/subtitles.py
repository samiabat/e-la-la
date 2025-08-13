from typing import Optional, List, Dict
import ffmpeg
import tempfile
import os

try:
    import whisper
except Exception:  # optional dependency fallback
    whisper = None


def burn_subtitles_karaoke(
    input_path: str,
    output_path: str,
    model: str = "tiny",
    font: str = "Poppins",
    font_size: int = 48,
    primary_color: str = "&H00FFFFFF&",  # Base text color
    highlight_color: str = "&H0000FF00&",  # Color while word is spoken
    outline_color: str = "&H00000000&",
    outline: int = 3,
    shadow: int = 0,
    margin_left: int = 100,
    margin_right: int = 100,
    margin_bottom: int = 160,
):
    """
    Transcribe with Whisper (if available) and burn animated karaoke-style subtitles.
    If Whisper is unavailable, this no-ops and just copies the input.
    """
    if whisper is None:
        # pass-through
        ffmpeg.input(input_path).output(output_path, c='copy', movflags='faststart').overwrite_output().run(quiet=True)
        return

    tmpdir = tempfile.mkdtemp()
    ass_path = os.path.join(tmpdir, 'subs.ass')

    model_obj = whisper.load_model(model)
    res = model_obj.transcribe(input_path, word_timestamps=True)

    # Build ASS with karaoke effect using \k tags
    def ass_time(sec: float) -> str:
        # ASS uses h:mm:ss.cs (centiseconds)
        cs = int(round(sec * 100))
        h = cs // (100*3600)
        cs -= h * (100*3600)
        m = cs // (100*60)
        cs -= m * (100*60)
        s = cs // 100
        cs -= s * 100
        return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font},{font_size},{primary_color},{highlight_color},{outline_color},&H00000000&,0,0,0,0,100,100,0,0,1,{outline},{shadow},2,{margin_left},{margin_right},{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines: List[str] = [header]
    for seg in res.get('segments', []):
        words: List[Dict] = seg.get('words') or []
        if not words:
            # fallback to whole segment
            text = (seg.get('text') or '').strip()
            if not text:
                continue
            start, end = float(seg['start']), float(seg['end'])
            line = f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{text}"
            lines.append(line)
            continue

        start = float(words[0]['start'])
        end = float(words[-1]['end'])
        # Build per-word karaoke: {\k<centiseconds>}word
        parts: List[str] = []
        prev = start
        for i, w in enumerate(words):
            w_start = float(w.get('start', prev))
            w_end = float(w.get('end', w_start))
            dur_cs = max(1, int(round((w_end - w_start) * 100)))
            token = (w.get('word') or w.get('text') or '')
            # escape braces
            token = token.replace('{', '\\{').replace('}', '\\}')
            parts.append(f"{{\\k{dur_cs}}}{token}")
            if i < len(words) - 1:
                parts.append(' ')
            prev = w_end
        payload = ''.join(parts)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{payload}")

    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    inp = ffmpeg.input(input_path)
    styled = inp.video.filter('subtitles', ass_path)
    (
        ffmpeg
        .output(styled, inp.audio, output_path, **{'c:v': 'libx264', 'c:a': 'copy', 'movflags': 'faststart'})
        .overwrite_output()
        .run(quiet=True)
    )
