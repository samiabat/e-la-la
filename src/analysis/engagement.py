from typing import Tuple, List, Sequence
import numpy as np
import librosa
import cv2

# Simple engagement heuristic: combine short-window audio RMS energy with frame diff-based motion

def _score_series(path: str, window_sec: float = 2.0, stride_sec: float = 0.5) -> Tuple[np.ndarray, float, float]:
    """
    Internal: compute engagement score per window along the video.
    Returns (scores array, stride_sec, window_sec).
    """
    """
    Returns (start_sec, score) for the best window.
    """
    # Audio energy
    y, sr = librosa.load(path, sr=None, mono=True)
    hop = int(stride_sec * sr)
    win = int(window_sec * sr)
    rms = []
    for s in range(0, max(1, len(y) - win), hop):
        seg = y[s:s+win]
        if len(seg) == 0:
            continue
        rms.append(float(np.sqrt(np.mean(seg**2))))
    rms = np.array(rms) if rms else np.array([0.0])

    # Visual motion via frame diffs
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        # fallback to audio-only
        motion_series = np.zeros_like(rms)
    else:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frames_per_win = int(window_sec * fps)
        frames_per_stride = max(1, int(stride_sec * fps))
        diffs = []
        ok, prev = cap.read()
        if ok:
            prev = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        frame_index = 0
        acc = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            d = cv2.absdiff(g, prev)
            prev = g
            acc.append(float(np.mean(d)))
            frame_index += 1
        cap.release()
        if not acc:
            motion_series = np.zeros_like(rms)
        else:
            acc = np.array(acc)
            # windowed mean over visual diffs to align with audio windows count
            num_windows = len(rms)
            if num_windows <= 1:
                motion_series = np.array([float(np.mean(acc))])
            else:
                # resample by averaging chunks
                idxs = np.linspace(0, len(acc), num_windows + 1).astype(int)
                chunks = [acc[idxs[i]:idxs[i+1]] for i in range(num_windows)]
                motion_series = np.array([float(np.mean(c)) if len(c) else 0.0 for c in chunks])

    # Normalize and combine
    def norm(x):
        if len(x) == 0:
            return x
        m, s = float(np.mean(x)), float(np.std(x) + 1e-6)
        return (x - m) / s

    audio_n = norm(rms)
    motion_n = norm(motion_series)
    score = 0.6 * audio_n + 0.4 * motion_n
    return score, stride_sec, window_sec


def best_window(path: str, window_sec: float = 2.0, stride_sec: float = 0.5) -> Tuple[float, float]:
    """Returns (start_sec, score) for the best window."""
    score, stride, _win = _score_series(path, window_sec=window_sec, stride_sec=stride_sec)
    best_idx = int(np.argmax(score)) if len(score) else 0
    start_sec = best_idx * stride
    return start_sec, float(score[best_idx] if len(score) else 0.0)


def top_windows_multi(
    path: str,
    durations: Sequence[float],
    stride_sec: float = 1.0,
    max_clips: int = 3,
    min_gap_sec: float = 1.0,
) -> List[Tuple[float, float, float]]:
    """
    Return up to max_clips non-overlapping windows across multiple durations.
    Each tuple is (start_sec, duration_sec, score).
    """
    candidates: List[Tuple[float, float, float]] = []
    for dur in durations:
        s, stride, win = _score_series(path, window_sec=float(dur), stride_sec=float(stride_sec))
        for i, sc in enumerate(s):
            start = i * stride
            candidates.append((start, float(dur), float(sc)))

    # sort by score desc
    candidates.sort(key=lambda t: t[2], reverse=True)

    chosen: List[Tuple[float, float, float]] = []
    def overlaps(a, b) -> bool:
        a0, a1 = a[0], a[0] + a[1]
        b0, b1 = b[0], b[0] + b[1]
        return not (a1 + min_gap_sec <= b0 or b1 + min_gap_sec <= a0)

    for cand in candidates:
        if len(chosen) >= max_clips:
            break
        if any(overlaps(cand, c) for c in chosen):
            continue
        chosen.append(cand)
    # sort chosen by start time for nicer ordering
    chosen.sort(key=lambda t: t[0])
    return chosen
