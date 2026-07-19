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
        if not generate_video(image_path, audio_path, title, features, output_path):
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

def generate_video(image_path, audio_path, title, features, output_path):
    """Generate video using FFmpeg"""
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Failed to read image")
            return False
        
        height, width = img.shape[:2]
        
        # Create video frames with text overlays
        frames_dir = f'temp/frames_{datetime.now().timestamp()}'
        os.makedirs(frames_dir, exist_ok=True)
        
        # Get audio duration
        audio_duration = get_audio_duration(audio_path)
        if audio_duration is None:
            audio_duration = 40
        
        fps = 30
        total_frames = int(audio_duration * fps)
        
        print(f"🎬 Creating {total_frames} frames at {fps}fps...")
        
        # Create frames
        for frame_num in range(total_frames):
            frame = img.copy()
            progress = frame_num / total_frames
            
            # Add title with fade-in effect
            alpha = min(1.0, progress * 3)  # Fade in over first 1/3
            if alpha > 0:
                add_text(frame, title, (width//2, 100), font_scale=2, alpha=alpha, color=(255, 255, 255))
            
            # Add features with sliding effect
            feature_alpha = min(1.0, max(0, (progress - 0.2) * 2))
            if feature_alpha > 0:
                y_pos = 250
                for i, feature in enumerate(features[:3]):
                    add_text(frame, f"• {feature}", (100, y_pos + i*60), font_scale=1.2, alpha=feature_alpha, color=(0, 255, 100))
            
            # Add CTA at end
            cta_alpha = min(1.0, max(0, (progress - 0.7) * 3))
            if cta_alpha > 0:
                add_text(frame, "Order Now!", (width//2, height - 100), font_scale=2, alpha=cta_alpha, color=(0, 100, 255))
            
            # Save frame
            frame_path = f'{frames_dir}/frame_{frame_num:06d}.png'
            cv2.imwrite(frame_path, frame)
            
            if frame_num % 30 == 0:
                print(f"  ✓ Frame {frame_num}/{total_frames}")
        
        print("🎬 Assembling video with FFmpeg...")
        
        # Use FFmpeg to create video
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', f'{frames_dir}/frame_%06d.png',
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
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

def add_text(frame, text, position, font_scale=1, alpha=1.0, color=(255, 255, 255)):
    """Add text to frame with alpha blending"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2
    
    # Get text size
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    x, y = position
    
    # Create text overlay
    overlay = frame.copy()
    cv2.putText(overlay, text, (x - text_size[0]//2, y), font, font_scale, color, thickness)
    
    # Blend
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

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
