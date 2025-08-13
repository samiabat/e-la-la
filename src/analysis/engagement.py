from typing import Tuple
import numpy as np
import librosa
import cv2

# Simple engagement heuristic: combine short-window audio RMS energy with frame diff-based motion

def best_window(path: str, window_sec: float = 2.0, stride_sec: float = 0.5) -> Tuple[float, float]:
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
    best_idx = int(np.argmax(score)) if len(score) else 0
    start_sec = best_idx * stride_sec
    return start_sec, float(score[best_idx] if len(score) else 0.0)
