from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
import os
import cv2
import numpy as np
from datetime import datetime
import subprocess
import json
from pathlib import Path
import sys

app = Flask(__name__)
CORS(app)

# Create directories
os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Try importing TTS libraries
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️  gTTS not installed. Run: pip install gtts")

@app.route('/')
def serve_home():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'home.html')

@app.route('/<path:filename>')
def serve_static_html(filename):
    if not filename.endswith('.html'):
        return jsonify({'error': 'Not found'}), 404
    directory = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(directory, filename)):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory(directory, filename)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'message': 'Product Ad Generator is running',
        'tts_available': TTS_AVAILABLE
    })

@app.route('/api/generate-ad', methods=['POST'])
def generate_ad():
    try:
        # Get input data
        data = request.form
        title = data.get('title', 'Amazing Product')
        features = data.get('features', '').split(',')
        features = [f.strip() for f in features if f.strip()]
        cta = data.get('cta', 'Buy Now')
        
        # Handle image upload
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        image_file = request.files['image']
        image_path = f'uploads/{datetime.now().timestamp()}.png'
        image_file.save(image_path)
        
        print(f"📸 Image saved: {image_path}")
        print(f"📝 Title: {title}")
        print(f"✨ Features: {features}")
        
        # Generate script
        script = generate_script(title, features, cta)
        print(f"📖 Script: {script}")
        
        # Generate audio (TTS)
        audio_path = f'temp/{datetime.now().timestamp()}.mp3'
        if not generate_audio(script, audio_path):
            return jsonify({'error': 'Failed to generate audio. Install: pip install gtts'}), 500
        
        print(f"🔊 Audio generated: {audio_path}")
        
        # Generate video
        output_path = f'outputs/ad_{datetime.now().timestamp()}.mp4'
        if not generate_video(image_path, audio_path, title, features, cta, output_path):
            return jsonify({'error': 'Failed to generate video. Install FFmpeg'}), 500
        
        print(f"✅ Video generated: {output_path}")
        
        # Cleanup
        os.remove(image_path)
        os.remove(audio_path)
        
        return jsonify({
            'success': True,
            'message': 'Ad generated successfully!',
            'video_url': f'/api/download/{os.path.basename(output_path)}'
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

MONTAGE_WIDTH = 720
MONTAGE_HEIGHT = 1280
MONTAGE_FPS = 12
MONTAGE_SECONDS_PER_IMAGE = 7.0
MONTAGE_TRANSITION_SECONDS = 0.5
MONTAGE_MIN_DURATION = 25
MONTAGE_MAX_DURATION = 30
MONTAGE_TITLE_SECONDS = 2.6
MONTAGE_FEATURES_SLIDE_SECONDS = 5.0
MONTAGE_CTA_SLIDE_SECONDS = 3.5
MONTAGE_MAX_FEATURES = 3
MONTAGE_PHOTO_MAX_ZOOM = 0.06
SLIDE_GRADIENT_TOP = (234, 126, 102)     # BGR for #667eea
SLIDE_GRADIENT_BOTTOM = (162, 75, 118)   # BGR for #764ba2
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'rizzova_logo.png')
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}

CLASSIC_WIDTH = 1080
CLASSIC_HEIGHT = 1920
CLASSIC_MIN_DURATION = 25
CLASSIC_MAX_DURATION = 30

@app.route('/api/generate-montage', methods=['POST'])
def generate_montage():
    try:
        data = request.form
        title = data.get('title', '').strip()
        features = data.get('features', '').split(',')
        features = [f.strip() for f in features if f.strip()]
        cta = data.get('cta', '').strip()
        link = data.get('link', '').strip()

        image_files = request.files.getlist('images')
        if not image_files:
            return jsonify({'error': 'No images uploaded'}), 400

        if 'music' not in request.files or request.files['music'].filename == '':
            return jsonify({'error': 'No music file uploaded'}), 400

        music_file = request.files['music']
        music_ext = os.path.splitext(music_file.filename)[1].lower()
        if music_ext not in ALLOWED_AUDIO_EXTENSIONS:
            return jsonify({'error': f'Unsupported music file type: {music_ext}'}), 400

        run_id = datetime.now().timestamp()
        image_paths = []
        for i, image_file in enumerate(image_files):
            image_path = f'uploads/montage_{run_id}_{i}.png'
            image_file.save(image_path)
            image_paths.append(image_path)

        music_path = f'temp/montage_music_{run_id}{music_ext}'
        music_file.save(music_path)

        print(f"📸 {len(image_paths)} images saved for montage")
        print(f"🎵 Music saved: {music_path}")

        output_path = f'outputs/montage_{run_id}.mp4'
        if not generate_montage_video(image_paths, music_path, title, features, cta, link, output_path):
            return jsonify({'error': 'Failed to generate montage video'}), 500

        print(f"✅ Montage generated: {output_path}")

        for p in image_paths:
            os.remove(p)
        os.remove(music_path)

        return jsonify({
            'success': True,
            'message': 'Montage generated successfully!',
            'video_url': f'/api/download/{os.path.basename(output_path)}'
        })

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def resize_cover(img, target_w, target_h):
    """Resize and center-crop an image to exactly fill target_w x target_h."""
    h, w = img.shape[:2]
    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale) + 1, int(h * scale) + 1
    resized = cv2.resize(img, (new_w, new_h))
    x0 = (new_w - target_w) // 2
    y0 = (new_h - target_h) // 2
    return resized[y0:y0 + target_h, x0:x0 + target_w]

def resize_contain_blurred(img, target_w, target_h):
    """Fit the whole image inside the frame with no cropping, centered over a
    softly blurred, dimmed version of itself so there are no dead bars."""
    h, w = img.shape[:2]

    bg = resize_cover(img, target_w, target_h)
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=35)
    bg = (bg.astype(np.float32) * 0.5).astype(np.uint8)

    scale = min(target_w / w, target_h / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    fitted = cv2.resize(img, (new_w, new_h))

    x0 = (target_w - new_w) // 2
    y0 = (target_h - new_h) // 2
    frame = bg
    frame[y0:y0 + new_h, x0:x0 + new_w] = fitted
    return frame

def apply_ken_burns_zoom(img, local_progress, max_zoom=0.15):
    """Crop progressively tighter toward center to simulate a zoom-in."""
    h, w = img.shape[:2]
    zoom = 1.0 + max_zoom * local_progress
    crop_w = int(w / zoom)
    crop_h = int(h / zoom)
    x0 = (w - crop_w) // 2
    y0 = (h - crop_h) // 2
    cropped = img[y0:y0 + crop_h, x0:x0 + crop_w]
    return cv2.resize(cropped, (w, h))

def make_gradient_bg(width, height, top_color, bottom_color):
    """Solid vertical gradient background for text slides."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for c in range(3):
        frame[:, :, c] = np.linspace(top_color[c], bottom_color[c], height, dtype=np.uint8)[:, None]
    return frame

def fit_font_scale(text, max_width, base_scale, font=cv2.FONT_HERSHEY_SIMPLEX, thickness=2, min_scale=0.5):
    """Shrink font scale until the text fits within max_width, so long strings never get clipped."""
    scale = base_scale
    while scale > min_scale:
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        if text_size[0] <= max_width:
            return scale
        scale -= 0.1
    return min_scale

def draw_centered_text(frame, text, y, max_width_ratio=0.85, base_scale=1.4, color=(255, 255, 255), alpha=1.0, thickness=2, outline=True):
    """Draw horizontally-centered text, auto-shrinking to fit within the frame width."""
    if not text or alpha <= 0:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    width = frame.shape[1]
    max_width = int(width * max_width_ratio)
    scale = fit_font_scale(text, max_width, base_scale, font, thickness)
    text_size = cv2.getTextSize(text, font, scale, thickness)[0]
    x = (width - text_size[0]) // 2
    overlay = frame.copy()
    if outline:
        cv2.putText(overlay, text, (x, y), font, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(overlay, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, min(1.0, alpha), frame, 1 - min(1.0, alpha), 0, frame)

def wrap_text_lines(text, font, scale, thickness, max_width):
    """Greedily wrap text into lines that each fit within max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if cv2.getTextSize(trial, font, scale, thickness)[0][0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def draw_wrapped_centered_text(frame, text, center_y, max_width_ratio=0.82, base_scale=1.7,
                                color=(255, 255, 255), alpha=1.0, thickness=3, max_lines=2,
                                min_scale=0.7, line_spacing=1.35):
    """Draw short, prominent title text centered on the frame (both axes), wrapping onto
    a couple of lines instead of shrinking illegibly small, with a dark outline so it stays
    readable over any photo."""
    if not text or alpha <= 0:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    width = frame.shape[1]
    max_width = int(width * max_width_ratio)

    scale = base_scale
    lines = wrap_text_lines(text, font, scale, thickness, max_width)
    while scale > min_scale and (len(lines) > max_lines or
                                  any(cv2.getTextSize(l, font, scale, thickness)[0][0] > max_width for l in lines)):
        scale -= 0.1
        lines = wrap_text_lines(text, font, scale, thickness, max_width)
    lines = lines[:max_lines]

    line_height = cv2.getTextSize("Ag", font, scale, thickness)[0][1]
    gap = int(line_height * line_spacing)
    total_h = gap * (len(lines) - 1)
    start_y = int(center_y - total_h / 2)

    overlay = frame.copy()
    for i, line in enumerate(lines):
        size = cv2.getTextSize(line, font, scale, thickness)[0]
        x = (width - size[0]) // 2
        y = start_y + i * gap
        cv2.putText(overlay, line, (x, y), font, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
        cv2.putText(overlay, line, (x, y), font, scale, color, thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, min(1.0, alpha), frame, 1 - min(1.0, alpha), 0, frame)

def draw_cta_button(frame, text, center_y, alpha=1.0, base_scale=1.7, text_color=(20, 20, 20),
                     button_color=(80, 200, 255), thickness=3, pad_x=55, pad_y=28):
    """Draw text on a solid pill-style button instead of bare on the background, so the
    call-to-action reads as a real button rather than floating text."""
    if not text or alpha <= 0:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    width = frame.shape[1]
    max_width = int(width * 0.78)
    scale = fit_font_scale(text, max_width, base_scale, font, thickness)
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x = (width - tw) // 2

    overlay = frame.copy()
    rect_x0, rect_y0 = x - pad_x, center_y - th - pad_y
    rect_x1, rect_y1 = x + tw + pad_x, center_y + baseline + pad_y // 2
    cv2.rectangle(overlay, (rect_x0, rect_y0), (rect_x1, rect_y1), button_color, -1, cv2.LINE_AA)
    cv2.putText(overlay, text, (x, center_y), font, scale, text_color, thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, min(1.0, alpha), frame, 1 - min(1.0, alpha), 0, frame)

def draw_bullet_list(frame, items, center_y, base_scale=3.0, color=(255, 255, 255), alpha=1.0,
                      thickness=5, max_width_ratio=0.85, line_spacing=1.5, min_scale=0.8):
    """Draw each item as its own big, bold bullet line (not wrapped/merged), all sharing one
    font size so the list reads as a clean stacked list of benefits."""
    lines = [f"• {item}" for item in items if item]
    if not lines or alpha <= 0:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    width = frame.shape[1]
    max_width = int(width * max_width_ratio)

    scale = base_scale
    while scale > min_scale and any(cv2.getTextSize(l, font, scale, thickness)[0][0] > max_width for l in lines):
        scale -= 0.1

    line_height = cv2.getTextSize("Ag", font, scale, thickness)[0][1]
    gap = int(line_height * line_spacing)
    total_h = gap * (len(lines) - 1)
    start_y = int(center_y - total_h / 2)

    overlay = frame.copy()
    for i, line in enumerate(lines):
        size = cv2.getTextSize(line, font, scale, thickness)[0]
        x = (width - size[0]) // 2
        y = start_y + i * gap
        cv2.putText(overlay, line, (x, y), font, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
        cv2.putText(overlay, line, (x, y), font, scale, color, thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, min(1.0, alpha), frame, 1 - min(1.0, alpha), 0, frame)

_logo_cache = {}

def load_logo():
    """Load the brand logo once and cache it; returns None if no logo asset has been added yet."""
    if LOGO_PATH not in _logo_cache:
        if os.path.exists(LOGO_PATH):
            _logo_cache[LOGO_PATH] = cv2.imread(LOGO_PATH, cv2.IMREAD_UNCHANGED)
        else:
            _logo_cache[LOGO_PATH] = None
    return _logo_cache[LOGO_PATH]

def draw_logo(frame, logo, center_y, alpha=1.0, target_height=110):
    """Composite the (optionally transparent) brand logo centered at center_y."""
    if logo is None or alpha <= 0:
        return
    h, w = logo.shape[:2]
    scale = target_height / h
    new_w, new_h = max(1, int(w * scale)), target_height
    resized = cv2.resize(logo, (new_w, new_h), interpolation=cv2.INTER_AREA)

    x0 = (frame.shape[1] - new_w) // 2
    y0 = center_y - new_h // 2
    x1, y1 = x0 + new_w, y0 + new_h
    if x0 < 0 or y0 < 0 or x1 > frame.shape[1] or y1 > frame.shape[0]:
        return

    roi = frame[y0:y1, x0:x1].astype(np.float32)
    if resized.shape[2] == 4:
        logo_alpha = (resized[:, :, 3:4].astype(np.float32) / 255.0) * alpha
        fg = resized[:, :, :3].astype(np.float32)
        frame[y0:y1, x0:x1] = (fg * logo_alpha + roi * (1 - logo_alpha)).astype(np.uint8)
    else:
        fg = resized[:, :, :3].astype(np.float32)
        frame[y0:y1, x0:x1] = (fg * alpha + roi * (1 - alpha)).astype(np.uint8)

def generate_montage_video(image_paths, music_path, title, features, cta, link, output_path):
    """Generate a structured montage: title card -> slow, crossfaded product photos ->
    feature slides -> CTA end card, synced to music."""
    try:
        images = []
        for p in image_paths:
            img = cv2.imread(p)
            if img is None:
                print(f"❌ Failed to read image: {p}")
                continue
            images.append(resize_contain_blurred(img, MONTAGE_WIDTH, MONTAGE_HEIGHT))

        if not images:
            print("❌ No valid images to build montage")
            return False

        features = [f.strip() for f in features if f.strip()][:MONTAGE_MAX_FEATURES]

        music_duration = get_audio_duration(music_path)
        if music_duration is None:
            music_duration = MONTAGE_MIN_DURATION
        total_duration = max(MONTAGE_MIN_DURATION, min(music_duration, MONTAGE_MAX_DURATION))

        fps = MONTAGE_FPS
        frames_per_image = max(1, int(MONTAGE_SECONDS_PER_IMAGE * fps))
        transition_frames = int(MONTAGE_TRANSITION_SECONDS * fps)
        title_card_frames = int(MONTAGE_TITLE_SECONDS * fps) if title else 0
        cta_frames = int(MONTAGE_CTA_SLIDE_SECONDS * fps)
        features_slide_frames = int(MONTAGE_FEATURES_SLIDE_SECONDS * fps) if features else 0

        total_frames = max(title_card_frames + frames_per_image + cta_frames, int(total_duration * fps))
        photo_frames = max(frames_per_image, total_frames - title_card_frames - cta_frames - features_slide_frames)

        print(f"🎬 Building montage: {title_card_frames} title-card frames, {photo_frames} photo frames, "
              f"{features_slide_frames} feature-slide frames, {cta_frames} CTA frames at {fps}fps")

        frames_dir = f'temp/montage_frames_{datetime.now().timestamp()}'
        os.makedirs(frames_dir, exist_ok=True)

        slide_bg = make_gradient_bg(MONTAGE_WIDTH, MONTAGE_HEIGHT, SLIDE_GRADIENT_TOP, SLIDE_GRADIENT_BOTTOM)
        logo = load_logo()
        num_images = len(images)
        do_photo_crossfade = num_images > 1 and transition_frames > 0

        # --- Segment renderers: each is a pure function of a local frame index, so we can
        # cheaply recompute any segment's final frame to crossfade into the next segment,
        # without having to buffer whole segments in memory. ---

        def render_title(j, length):
            frame = slide_bg.copy()
            local_progress = j / length
            if local_progress < 0.25:
                alpha = local_progress / 0.25
            elif local_progress > 0.8:
                alpha = max(0, (1.0 - local_progress) / 0.2)
            else:
                alpha = 1.0
            draw_wrapped_centered_text(frame, title, int(MONTAGE_HEIGHT * 0.42), base_scale=2.0,
                                        color=(255, 255, 255), alpha=alpha, thickness=4, max_lines=3)
            return frame

        def render_photo(i, length):
            slot = i // frames_per_image
            image_index = slot % num_images
            pos_in_slot = i % frames_per_image
            local_progress = pos_in_slot / frames_per_image
            frame = apply_ken_burns_zoom(images[image_index], local_progress, max_zoom=MONTAGE_PHOTO_MAX_ZOOM)

            if do_photo_crossfade and slot > 0 and pos_in_slot < transition_frames:
                prev_index = (image_index - 1) % num_images
                prev_frame = apply_ken_burns_zoom(images[prev_index], 1.0, max_zoom=MONTAGE_PHOTO_MAX_ZOOM)
                blend = (pos_in_slot + 1) / transition_frames
                frame = cv2.addWeighted(frame, blend, prev_frame, 1 - blend, 0)
            return frame

        def render_features(j, length):
            frame = slide_bg.copy()
            local_progress = j / length
            alpha = min(1.0, local_progress * 4)
            draw_bullet_list(frame, features, int(MONTAGE_HEIGHT * 0.46), base_scale=3.0,
                              color=(255, 255, 255), alpha=alpha, thickness=5)
            return frame

        def render_cta(j, length):
            frame = slide_bg.copy()
            local_progress = j / length
            alpha = min(1.0, local_progress * 4)
            if cta:
                draw_cta_button(frame, cta, MONTAGE_HEIGHT // 2 - 90, alpha=alpha, base_scale=1.7)
            if link:
                draw_centered_text(frame, link, MONTAGE_HEIGHT // 2 + 10, base_scale=1.0, color=(230, 230, 230), alpha=alpha, thickness=2)
            draw_logo(frame, logo, int(MONTAGE_HEIGHT * 0.72), alpha=alpha)
            return frame

        segments = []
        if title:
            segments.append((render_title, title_card_frames))
        segments.append((render_photo, photo_frames))
        if features:
            segments.append((render_features, features_slide_frames))
        segments.append((render_cta, cta_frames))

        # --- Write every segment, crossfading the opening of each into the frozen last
        # frame of the previous one so every transition dissolves instead of hard-cutting ---
        frame_num = 0
        prev_last_frame = None
        for render_fn, length in segments:
            for j in range(length):
                frame = render_fn(j, length)
                if prev_last_frame is not None and j < transition_frames:
                    blend = (j + 1) / transition_frames
                    frame = cv2.addWeighted(frame, blend, prev_last_frame, 1 - blend, 0)
                cv2.imwrite(f'{frames_dir}/frame_{frame_num:06d}.png', frame)
                frame_num += 1
                if frame_num % 30 == 0:
                    print(f"  ✓ Frame {frame_num}/{total_frames}")
            prev_last_frame = render_fn(length - 1, length)

        print("🎬 Assembling montage with FFmpeg...")

        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', f'{frames_dir}/frame_%06d.png',
            '-stream_loop', '-1',
            '-i', music_path,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-c:a', 'aac',
            '-t', str(total_duration),
            output_path
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ FFmpeg error: {result.stderr}")
            return False

        print(f"✅ Montage created: {output_path}")

        import shutil
        shutil.rmtree(frames_dir)

        return True

    except Exception as e:
        print(f"❌ Montage generation error: {e}")
        return False

def generate_script(title, features, cta):
    """Generate ad script"""
    script = f"Introducing {title}. "
    
    for i, feature in enumerate(features[:3], 1):
        script += f"Feature {i}: {feature}. "
    
    script += f"Don't miss out. {cta} today!"
    
    return script

def generate_audio(text, output_path):
    """Generate audio using free TTS"""
    try:
        if not TTS_AVAILABLE:
            print("⚠️  Installing gTTS...")
            os.system("pip install gtts")
        
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        return True
    except Exception as e:
        print(f"❌ Audio generation error: {e}")
        return False

def generate_video(image_path, audio_path, title, features, cta, output_path):
    """Generate video using FFmpeg"""
    try:
        # Read image and standardize to a vertical 9:16 canvas (best format
        # for TikTok/Reels/Shorts placement, matches the montage mode)
        raw_img = cv2.imread(image_path)
        if raw_img is None:
            print("❌ Failed to read image")
            return False

        img = resize_contain_blurred(raw_img, CLASSIC_WIDTH, CLASSIC_HEIGHT)
        width, height = CLASSIC_WIDTH, CLASSIC_HEIGHT

        # Create video frames with text overlays
        frames_dir = f'temp/frames_{datetime.now().timestamp()}'
        os.makedirs(frames_dir, exist_ok=True)

        # Get audio duration and clamp the video to a 25-30s window,
        # which performs best for completion rate on short-form platforms
        audio_duration = get_audio_duration(audio_path)
        if audio_duration is None:
            audio_duration = CLASSIC_MIN_DURATION
        total_duration = max(CLASSIC_MIN_DURATION, min(audio_duration, CLASSIC_MAX_DURATION))

        fps = 15
        total_frames = int(total_duration * fps)

        cta_text = cta.strip() if cta and cta.strip() else 'Order Now!'

        print(f"🎬 Creating {total_frames} frames at {fps}fps...")

        # Create frames
        for frame_num in range(total_frames):
            frame = img.copy()
            progress = frame_num / total_frames

            # Add title with fade-in effect, short and prominent like a hero headline
            alpha = min(1.0, progress * 3)  # Fade in over first 1/3
            if alpha > 0:
                draw_wrapped_centered_text(frame, title, int(height * 0.16), base_scale=2.4,
                                            color=(255, 255, 255), alpha=alpha, thickness=4, max_lines=2)

            # Add features, one clean centered line each, like feature callouts
            feature_alpha = min(1.0, max(0, (progress - 0.2) * 2))
            if feature_alpha > 0:
                y_pos = int(height * 0.30)
                for i, feature in enumerate(features[:3]):
                    draw_centered_text(frame, f"✓ {feature}", y_pos + i * 90, base_scale=1.5,
                                        color=(0, 255, 100), alpha=feature_alpha, thickness=3)

            # Add CTA at end
            cta_alpha = min(1.0, max(0, (progress - 0.7) * 3))
            if cta_alpha > 0:
                draw_centered_text(frame, cta_text, height - 110, base_scale=2, color=(0, 150, 255), alpha=cta_alpha, thickness=3)

            # Save frame
            frame_path = f'{frames_dir}/frame_{frame_num:06d}.png'
            cv2.imwrite(frame_path, frame)

            if frame_num % 30 == 0:
                print(f"  ✓ Frame {frame_num}/{total_frames}")

        print("🎬 Assembling video with FFmpeg...")

        # Use FFmpeg to create video. Audio is padded with silence (apad) if
        # shorter than the video and the whole output is capped at
        # total_duration, so the final length always lands in the 25-30s window.
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', f'{frames_dir}/frame_%06d.png',
            '-i', audio_path,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-af', 'apad',
            '-c:a', 'aac',
            '-t', str(total_duration),
            output_path
        ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ FFmpeg error: {result.stderr}")
            return False
        
        print(f"✅ Video created: {output_path}")
        
        # Cleanup frames
        import shutil
        shutil.rmtree(frames_dir)
        
        return True
    
    except Exception as e:
        print(f"❌ Video generation error: {e}")
        return False

def get_audio_duration(audio_path):
    """Get audio duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return None

@app.route('/api/download/<filename>', methods=['GET'])
def download_video(filename):
    """Download generated video"""
    try:
        video_path = f'outputs/{filename}'
        if not os.path.exists(video_path):
            return jsonify({'error': 'Video not found'}), 404
        
        return send_file(video_path, mimetype='video/mp4', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════╗
    ║  🎬 FREE PRODUCT AD GENERATOR         ║
    ║  Completely Open Source & Free        ║
    ╚════════════════════════════════════════╝
    """)
    
    # Check requirements
    print("📋 Checking requirements...")
    
    try:
        import cv2
        print("✅ OpenCV installed")
    except ImportError:
        print("⚠️  Install OpenCV: pip install opencv-python")
    
    try:
        from gtts import gTTS
        print("✅ gTTS installed")
    except ImportError:
        print("⚠️  Install gTTS: pip install gtts")
    
    # Check FFmpeg
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
    if result.returncode == 0:
        print("✅ FFmpeg installed")
    else:
        print("⚠️  Install FFmpeg: brew install ffmpeg (Mac) or apt-get install ffmpeg (Linux)")
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"\n🚀 Starting server on http://localhost:{port}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
