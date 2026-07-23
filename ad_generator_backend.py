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
MONTAGE_SECONDS_PER_IMAGE = 0.5
MONTAGE_MIN_DURATION = 25
MONTAGE_MAX_DURATION = 30
MONTAGE_TITLE_SECONDS = 2.5
MONTAGE_FEATURE_SLIDE_SECONDS = 1.8
MONTAGE_CTA_SLIDE_SECONDS = 3.0
MONTAGE_MAX_FEATURES = 3
SLIDE_GRADIENT_TOP = (234, 126, 102)     # BGR for #667eea
SLIDE_GRADIENT_BOTTOM = (162, 75, 118)   # BGR for #764ba2
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

def generate_montage_video(image_paths, music_path, title, features, cta, link, output_path):
    """Generate a structured montage: fast-cut hook photos -> feature slides -> CTA end card, synced to music."""
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
        title_frames = int(MONTAGE_TITLE_SECONDS * fps)
        cta_frames = int(MONTAGE_CTA_SLIDE_SECONDS * fps)
        feature_frames_each = int(MONTAGE_FEATURE_SLIDE_SECONDS * fps)
        feature_total_frames = feature_frames_each * len(features)

        total_frames = max(frames_per_image + cta_frames, int(total_duration * fps))
        photo_frames = max(frames_per_image, total_frames - cta_frames - feature_total_frames)

        print(f"🎬 Building montage: {photo_frames} hook-photo frames, "
              f"{feature_total_frames} feature-slide frames, {cta_frames} CTA frames at {fps}fps")

        frames_dir = f'temp/montage_frames_{datetime.now().timestamp()}'
        os.makedirs(frames_dir, exist_ok=True)

        slide_bg = make_gradient_bg(MONTAGE_WIDTH, MONTAGE_HEIGHT, SLIDE_GRADIENT_TOP, SLIDE_GRADIENT_BOTTOM)
        frame_num = 0

        # --- Segment 1: fast-cut hook photos, with the title held on top for a few seconds ---
        for i in range(photo_frames):
            image_index = (i // frames_per_image) % len(images)
            local_progress = (i % frames_per_image) / frames_per_image
            frame = apply_ken_burns_zoom(images[image_index], local_progress)

            if title and i < title_frames:
                title_progress = i / title_frames
                title_alpha = min(1.0, max(0, 1.0 - title_progress * 1.3))
                draw_wrapped_centered_text(frame, title, int(MONTAGE_HEIGHT * 0.38), base_scale=1.8,
                                            color=(255, 255, 255), alpha=title_alpha, thickness=3, max_lines=2)

            cv2.imwrite(f'{frames_dir}/frame_{frame_num:06d}.png', frame)
            frame_num += 1
            if frame_num % 30 == 0:
                print(f"  ✓ Frame {frame_num}/{total_frames}")

        # --- Segment 2: one clean slide per feature, no busy photo behind the text ---
        for feature in features:
            for j in range(feature_frames_each):
                frame = slide_bg.copy()
                local_progress = j / feature_frames_each
                alpha = min(1.0, local_progress * 5)
                draw_centered_text(frame, feature, MONTAGE_HEIGHT // 2, base_scale=1.6, color=(255, 255, 255), alpha=alpha, thickness=3)
                cv2.imwrite(f'{frames_dir}/frame_{frame_num:06d}.png', frame)
                frame_num += 1
                if frame_num % 30 == 0:
                    print(f"  ✓ Frame {frame_num}/{total_frames}")

        # --- Segment 3: dedicated CTA end card ---
        for j in range(cta_frames):
            frame = slide_bg.copy()
            local_progress = j / cta_frames
            alpha = min(1.0, local_progress * 4)
            if cta:
                draw_centered_text(frame, cta, MONTAGE_HEIGHT // 2 - 50, base_scale=1.8, color=(255, 255, 255), alpha=alpha, thickness=3)
            if link:
                draw_centered_text(frame, link, MONTAGE_HEIGHT // 2 + 50, base_scale=1.0, color=(220, 220, 220), alpha=alpha, thickness=2)
            cv2.imwrite(f'{frames_dir}/frame_{frame_num:06d}.png', frame)
            frame_num += 1
            if frame_num % 30 == 0:
                print(f"  ✓ Frame {frame_num}/{total_frames}")

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
