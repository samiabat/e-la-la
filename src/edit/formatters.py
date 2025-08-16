from typing import Tuple
import ffmpeg
import os
try:
    import cv2
except Exception:
    cv2 = None


def to_vertical(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    blur: int = 18,
    padding_color: str = 'black',
    fg_scale: float = 0.95,
    bg_brightness: float = 0.08,
    bg_saturation: float = 1.05,
    add_progress: bool = True,
    progress_height: int = 10,
    progress_color: str = 'white',
    progress_position: str = 'bottom',  # 'bottom' or 'top'
    grade: bool = True,
    grade_contrast: float = 1.06,
    grade_saturation: float = 1.04,
    add_vignette: bool = False,
    audio_enhance: bool = True,
    music_path: str = '',
    music_volume: float = 0.08,
    pulse_zoom: bool = False,
    pulse_amount: float = 0.02,
    pulse_freq: float = 1.1,
    auto_reframe: bool = False,
    reframe_samples: int = 9,
    hook_text: str = '',
    end_text: str = '',
):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid canvas size {width}x{height}")

    # Background canvas
    bg = (
        ffmpeg
        .input(input_path)
        .video
        .filter('scale', width, height, force_original_aspect_ratio='increase')
        .filter('crop', width, height)
        .filter('boxblur', blur)
        .filter('eq', brightness=bg_brightness, saturation=bg_saturation)
    )

    # Foreground scaled by height
    fg = (
        ffmpeg
        .input(input_path)
        .video
        .filter('scale', -2, int(height * fg_scale))
    )

    # Duration probe
    try:
        import ffmpeg as _ff
        _meta = _ff.probe(input_path)
        _fmt = _meta.get('format', {})
        dur = float(_fmt.get('duration', 0.0)) if _fmt.get('duration') else 0.0
    except Exception:
        dur = 0.0

    # Optional auto-reframe
    overlay_x_expr = '(W-w)/2'
    if auto_reframe and cv2 is not None:
        try:
            cap = cv2.VideoCapture(input_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            idxs = []
            if total > 0:
                step = max(1, total // max(1, reframe_samples))
                idxs = [min(i, total-1) for i in range(0, total, step)][:reframe_samples]
            else:
                idxs = [0]
            face_xs = []
            cascade_path = None
            try:
                import cv2.data as cvd
                cascade_path = os.path.join(cvd.haarcascades, 'haarcascade_frontalface_default.xml')
            except Exception:
                cascade_path = None
            detector = cv2.CascadeClassifier(cascade_path) if cascade_path and os.path.exists(cascade_path) else None
            if detector is not None:
                for idx in idxs:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        continue
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = detector.detectMultiScale(gray, 1.2, 3)
                    if len(faces) > 0:
                        x, y, w, h = max(faces, key=lambda b: b[2]*b[3])
                        cx = x + w/2.0
                        face_xs.append(cx)
                cap.release()
            if face_xs:
                try:
                    import ffmpeg as _ff
                    meta = _ff.probe(input_path)
                    vstream = next(s for s in meta['streams'] if s.get('codec_type') == 'video')
                    sw, sh = int(vstream['width']), int(vstream['height'])
                except Exception:
                    sw, sh = (1920, 1080)
                fg_h = int(height * fg_scale)
                fg_w = int(round(fg_h * (sw / sh)))
                avg_cx_src = sum(face_xs) / len(face_xs)
                scale_x = fg_w / float(sw)
                face_cx_fg = avg_cx_src * scale_x
                desired = width / 2.0 - face_cx_fg
                max_left = 0
                max_right = width - fg_w
                ovx = max(max_left, min(max_right, int(round(desired))))
                overlay_x_expr = str(ovx)
        except Exception:
            overlay_x_expr = '(W-w)/2'

    if overlay_x_expr == '(W-w)/2':
        overlay_x_expr = '(main_w-overlay_w)/2'
    video = ffmpeg.overlay(bg, fg, x=overlay_x_expr, y='(main_h-overlay_h)/2')

    # Grade / vignette
    if grade:
        video = video.filter('eq', contrast=grade_contrast, saturation=grade_saturation)
    if add_vignette:
        video = video.filter('vignette', angle='PI/4')

    # Progress bar (color + scale(t) with eval=frame, then overlay)
    if add_progress and dur > 0:
        safe_d = max(dur, 1e-3)
        bar = (
            ffmpeg
            .input(f'color=c={progress_color}@0.9:s={width}x{progress_height}:r=30:d={safe_d}', f='lavfi')
            .video
            .filter(
                'scale',
                f'ceil(min({width}, max(1,{width}*t/{safe_d})))',  # animated width by time
                f'{progress_height}',
                eval='frame'  # <<< REQUIRED so 't' is allowed
            )
            .filter('setsar', 1)
        )
        pos_y = 'main_h-overlay_h' if progress_position == 'bottom' else '0'
        video = ffmpeg.overlay(video, bar, x=0, y=pos_y, eof_action='repeat')

    # Hook / end text overlays
    try:
        if hook_text:
            video = video.filter('drawbox', x='(w*0.05)', y='h*0.2', w='w*0.9', h=120, color='black@0.35', t='fill', enable='lte(t,0.8)')
            video = video.filter('drawtext', text=hook_text, x='(w-text_w)/2', y='h*0.2 + (120-text_h)/2', fontsize=64, fontcolor='white@0.98', enable='lte(t,0.8)')
        if end_text and dur:
            tstart = max(0.0, dur - 1.0)
            video = video.filter('drawbox', x='(w*0.05)', y='h*0.75', w='w*0.9', h=120, color='black@0.35', t='fill', enable=f'gte(t,{tstart})')
            video = video.filter('drawtext', text=end_text, x='(w-text_w)/2', y='h*0.75 + (120-text_h)/2', fontsize=64, fontcolor='white@0.98', enable=f'gte(t,{tstart})')
    except Exception:
        pass

    # Optional micro zoom
    if pulse_zoom and pulse_amount > 0:
        zexpr = f"max(1, 1+{pulse_amount}*sin(2*PI*{pulse_freq}*t))"
        video = video.filter('zoompan', z=zexpr, d=1, s=f'{width}x{height}')

    video = video.filter('format', 'yuv420p')

    # Audio chain
    a_inp = ffmpeg.input(input_path)
    voice = a_inp.audio
    if audio_enhance:
        voice = (voice.filter('highpass', f=80).filter('dynaudnorm', f=150, g=15))
    audio = voice
    if music_path and os.path.exists(music_path):
        try:
            music = ffmpeg.input(music_path).audio.filter('volume', music_volume)
            ducked = ffmpeg.filter([music, voice], 'sidechaincompress', threshold=0.05, ratio=10, attack=5, release=250)
            audio = ffmpeg.filter([voice, ducked], 'amix', inputs=2, dropout_transition=0)
        except Exception:
            audio = voice
    if audio_enhance:
        audio = audio.filter('alimiter', limit=0.9)

    # Final render (stderr captured)
    try:
        (
            ffmpeg
            .output(
                video, audio, output_path,
                vcodec='libx264',
                acodec='aac',
                r=30,
                crf=20,
                preset='veryfast',
                movflags='faststart'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        try:
            err = e.stderr.decode('utf-8', errors='ignore')
        except Exception:
            err = str(e)
        print("\n===== FFmpeg stderr (to_vertical) =====\n")
        print(err)
        print("\n=======================================\n")
        raise


def cut_segment(input_path: str, output_path: str, start: float, duration: float):
    (
        ffmpeg
        .input(input_path, ss=start, t=duration)
        .output(output_path, c='copy', movflags='faststart')
        .overwrite_output()
        .run(quiet=True)
    )


def export_audio(input_path: str, output_path: str, bitrate: str = '192k'):
    a = ffmpeg.input(input_path).audio
    kwargs = {}
    if output_path.lower().endswith('.mp3'):
        kwargs.update({'acodec': 'libmp3lame', 'audio_bitrate': bitrate})
    (
        ffmpeg
        .output(a, output_path, **kwargs)
        .overwrite_output()
        .run(quiet=True)
    )
