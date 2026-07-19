@echo off
echo.
echo ╔════════════════════════════════════════════════╗
echo ║  🎬 FREE PRODUCT AD GENERATOR                 ║
echo ║  100%% Free, No Credit Card Needed           ║
echo ╚════════════════════════════════════════════════╝
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Install from https://python.org/
    pause
    exit /b 1
)
echo ✅ Python found

echo.
echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ❌ FFmpeg not found! Install it first.
    echo    Windows: choco install ffmpeg
    echo    Or download: https://ffmpeg.org/download.html
    pause
    exit /b 1
)
echo ✅ FFmpeg found

echo.
echo Installing Python packages...
pip install -r requirements.txt

echo.
echo ✅ All ready!
echo.
echo 🚀 Starting Free Ad Generator...
echo 📍 Visit: http://localhost:5000/ad_generator.html
echo.

python ad_generator_backend.py

pause
