from typing import Optional, List, Tuple
import math

# Optional whisper import
try:
    import whisper
except Exception:
    whisper = None

from pydub import AudioSegment, silence


def transcribe_with_words(path: str, model: str = "tiny") -> Optional[dict]:
    if whisper is None:
        return None
    try:
        m = whisper.load_model(model)
        return m.transcribe(path, word_timestamps=True)
    except Exception:
        return None


def detect_silences(path: str, min_silence_len_ms: int = 400, silence_db_drop: float = 16.0) -> List[Tuple[float, float]]:
    """Return list of silence intervals as (start_sec, end_sec)."""
    audio = AudioSegment.from_file(path)
    thresh = audio.dBFS - silence_db_drop
    sils = silence.detect_silence(audio, min_silence_len=min_silence_len_ms, silence_thresh=thresh)
    return [(s/1000.0, e/1000.0) for s, e in sils]


def pick_idea_endpoint(
    transcript: Optional[dict],
    silences: List[Tuple[float, float]],
    start_hint: float,
    min_dur: float = 20.0,
    max_dur: float = 120.0,
) -> float:
    """
    Choose an end time based on transcript punctuation boundaries and/or silence, constrained within [start+min_dur, start+max_dur].
    Preference: nearest sentence end >= min_dur; else nearest silence >= min_dur; else fallback to max_dur.
    """
    min_end = start_hint + min_dur
    max_end = start_hint + max_dur

    cand_transcript: Optional[float] = None
    if transcript is not None:
        for seg in transcript.get('segments', []):
            seg_end = float(seg.get('end', 0.0))
            if seg_end < min_end or seg_end > max_end:
                continue
            text = (seg.get('text') or '').strip()
            if text.endswith(('.', '!', '?')):
                cand_transcript = seg_end
                break
        if cand_transcript is None:
            # fallback to first segment end within range
            for seg in transcript.get('segments', []):
                seg_end = float(seg.get('end', 0.0))
                if seg_end >= min_end and seg_end <= max_end:
                    cand_transcript = seg_end
                    break

    cand_silence: Optional[float] = None
    for s, e in silences:
        if s >= min_end and s <= max_end:
            cand_silence = s
            break

    # Decide
    if cand_transcript is not None and cand_silence is not None:
        # pick the earlier boundary after min_end
        return min(cand_transcript, cand_silence)
    if cand_transcript is not None:
        return cand_transcript
    if cand_silence is not None:
        return cand_silence
    return max_end
