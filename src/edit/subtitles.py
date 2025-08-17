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
    font_size: int = 72,  # Increased from 48 to make text bigger
    primary_color: str = "&H00FFFFFF&",  # ASS BGR with &H..& format
    secondary_color: str = "&H0000FF00&",  # highlight color for karaoke effect
    outline_color: str = "&H00000000&",
    outline: int = 5,  # Increased from 3 to make text thicker
    shadow: int = 0,
    margin_lr: int = 80,
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
Style: Karaoke,{font},{font_size},{primary_color},{secondary_color},{outline_color},&H00000000&,1,0,0,0,100,100,0,0,1,{outline},{shadow},5,{margin_lr},{margin_lr},{margin_bottom},1

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

        # Group words into chunks of 3
        word_chunks = []
        for i in range(0, len(words), 3):
            chunk = words[i:i+3]
            word_chunks.append(chunk)
        
        for chunk in word_chunks:
            if not chunk:
                continue
                
            chunk_start = float(chunk[0]['start'])
            chunk_end = float(chunk[-1]['end'])
            
            # Build text for this chunk (3 words max)
            chunk_text_parts = []
            for w in chunk:
                token = (w.get('word') or w.get('text') or '').strip()
                if token:
                    chunk_text_parts.append(token)
            
            if chunk_text_parts:
                chunk_text = ' '.join(chunk_text_parts)
                # Escape braces for ASS format
                chunk_text = chunk_text.replace('{', '\\{').replace('}', '\\}')
                line = f"Dialogue: 0,{ass_time(chunk_start)},{ass_time(chunk_end)},Karaoke,,0,0,0,,{chunk_text}"
                lines.append(line)

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
