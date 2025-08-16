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
    font: str = "DejaVu Sans",
    font_size: int = 110,
    primary_color: str = "&H00FFFFFF&",  # white text
    secondary_color: str = "&H0000FF00&",  # green karaoke fill
    outline_color: str = "&H00101010&",
    outline: int = 8,
    shadow: int = 3,
    box_color: str = "&H80202020&",  # semi-transparent dark box
    words_per_chunk: int = 3,
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
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; Centered background box behind text
Style: CenterBox,{font},{font_size},{primary_color},{secondary_color},{outline_color},{box_color},1,0,0,0,100,100,0,0,3,0,0,5,0,0,0,1
; Centered thick foreground text with karaoke fill
Style: CenterFG,{font},{font_size},{primary_color},{secondary_color},{outline_color},&H00000000&,1,0,0,0,100,100,0,0,1,{outline},{shadow},5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines: List[str] = [header]
    wrap_tag = "{\\q0}"
    for seg in res.get('segments', []):
        words: List[Dict] = seg.get('words') or []
        if not words:
            # fallback to whole segment
            text = (seg.get('text') or '').strip()
            if not text:
                continue
            start, end = float(seg['start']), float(seg['end'])
            # Centered single line (no per-word timing available)
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},CenterBox,,0,0,0,,{wrap_tag}{text}")
            lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},CenterFG,,0,0,0,,{wrap_tag}{text}")
            continue

        # Chunk into 2–3 word phrases centered on screen
        n = max(1, int(words_per_chunk))
        i = 0
        while i < len(words):
            chunk = words[i:i+n]
            cstart = float(chunk[0].get('start', 0.0))
            cend = float(chunk[-1].get('end', cstart))
            # Plain text for box
            plain = ' '.join([(w.get('word') or w.get('text') or '').strip() for w in chunk]).strip()
            # Karaoke payload for foreground
            parts: List[str] = []
            prev = cstart
            for j, w in enumerate(chunk):
                w_start = float(w.get('start', prev))
                w_end = float(w.get('end', w_start))
                dur_cs = max(1, int(round((w_end - w_start) * 100)))
                token = (w.get('word') or w.get('text') or '').strip()
                token = token.replace('{', '\\{').replace('}', '\\}')
                if j > 0:
                    parts.append(' ')
                parts.append(f"{{\\k{dur_cs}}}{token}")
                prev = w_end
            payload = ''.join(parts)
            lines.append(f"Dialogue: 0,{ass_time(cstart)},{ass_time(cend)},CenterBox,,0,0,0,,{wrap_tag}{plain}")
            lines.append(f"Dialogue: 1,{ass_time(cstart)},{ass_time(cend)},CenterFG,,0,0,0,,{wrap_tag}{payload}")
            i += n

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
