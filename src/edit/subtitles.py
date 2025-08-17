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
    font_size: int = 108,  # 2x larger
    primary_color: str = "&H00FFFFFF&",  # ASS BGR with &H..& format
    secondary_color: str = "&H0000FF00&",  # highlight color for karaoke effect
    outline_color: str = "&H00000000&",
    outline: int = 16,  # 2x thicker outline
    shadow: int = 0,
    margin_lr: int = 80,
    margin_bottom: int = 0,  # use as center offset when centered
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

    # chunking preferences
    MIN_WORDS = 2
    MAX_WORDS = 4

    def make_payload_from_words(words_chunk: List[Dict]) -> str:
        # Build per-word karaoke: {\k<centiseconds>}word for the chunk
        parts: List[str] = []
        prev_local = float(words_chunk[0].get('start', 0.0))
        for w in words_chunk:
            w_start = float(w.get('start', prev_local))
            w_end = float(w.get('end', w_start))
            dur_cs = max(1, int(round((w_end - w_start) * 100)))
            token = (w.get('word') or w.get('text') or '')
            token = token.replace('{', '\\{').replace('}', '\\}')
            if parts and not token.startswith(' '):
                token = ' ' + token
            parts.append(f"{{\\k{dur_cs}}}{token}")
            prev_local = w_end
        return ''.join(parts)

    def should_break_at_token(token: str) -> bool:
        t = (token or '').strip()
        return t.endswith(('.', '!', '?', ',', ';', ':'))
    for seg in res.get('segments', []):
        words: List[Dict] = seg.get('words') or []
        if not words:
            # Fallback: approximate timings by evenly distributing words in the segment
            text = (seg.get('text') or '').strip()
            if not text:
                continue
            start, end = float(seg['start']), float(seg['end'])
            tokens = text.split()
            n = len(tokens)
            if n == 0:
                continue
            per_dur = (end - start) / max(1, n)
            i = 0
            while i < n:
                # choose a chunk size between MIN_WORDS and MAX_WORDS
                chunk_end_idx = min(n, i + MAX_WORDS)
                # allow early break on punctuation if we already have MIN_WORDS
                chosen_end = chunk_end_idx
                for j in range(i + MIN_WORDS, chunk_end_idx + 1):
                    if j <= n and should_break_at_token(tokens[j - 1]):
                        chosen_end = j
                        break
                j = chosen_end
                chunk_tokens = tokens[i:j]
                c_start = start + i * per_dur
                c_end = start + j * per_dur
                # Build simple \k payload with equal per-word duration
                dur_cs = max(1, int(round(per_dur * 100)))
                parts = []
                for idx, tok in enumerate(chunk_tokens):
                    tok = tok.replace('{', '\\{').replace('}', '\\}')
                    if idx > 0 and not tok.startswith(' '):
                        tok = ' ' + tok
                    parts.append(f"{{\\k{dur_cs}}}{tok}")
                payload = ''.join(parts)
                lines.append(f"Dialogue: 0,{ass_time(c_start)},{ass_time(c_end)},Karaoke,,0,0,0,,{payload}")
                i = j
            continue

        start = float(words[0]['start'])
        end = float(words[-1]['end'])
        # Create multiple dialogues, each with 2-4 words, centered
        i = 0
        n = len(words)
        while i < n:
            # Determine chunk end respecting punctuation and word limits
            chunk_end_idx = min(n, i + MAX_WORDS)
            chosen_end = chunk_end_idx
            for j in range(i + MIN_WORDS, chunk_end_idx + 1):
                if j <= n and should_break_at_token((words[j - 1].get('word') or words[j - 1].get('text') or '')):
                    chosen_end = j
                    break
            j = chosen_end
            chunk = words[i:j]
            c_start = float(chunk[0].get('start', start))
            c_end = float(chunk[-1].get('end', c_start))
            payload = make_payload_from_words(chunk)
            lines.append(f"Dialogue: 0,{ass_time(c_start)},{ass_time(c_end)},Karaoke,,0,0,0,,{payload}")
            i = j

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
