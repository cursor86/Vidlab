#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  🎬 FREE PRODUCT AD GENERATOR                 ║"
echo "║  100% Free, No Credit Card Needed            ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found! Install from https://python.org/"
    exit 1
fi
python3 --version
echo "✅ Python found"

echo ""
echo "Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found!"
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt-get install ffmpeg"
    exit 1
fi
ffmpeg -version | head -n 1
echo "✅ FFmpeg found"

echo ""
echo "Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "✅ All ready!"
echo ""
echo "🚀 Starting Free Ad Generator..."
echo "📍 Visit: http://localhost:5000/ad_generator.html"
echo ""

python3 ad_generator_backend.py
