#!/bin/bash

echo "🚀 AI_CURSOR SETUP STARTED"

# Exit if Python 3.10 is not installed
if ! command -v python3.10 &> /dev/null; then
    echo "❌ Python 3.10 not found. Install with: brew install python@3.10"
    exit 1
fi

# Remove old venv
echo "🧹 Removing old virtual environment..."
rm -rf venv

# Create new venv
echo "🐍 Creating virtual environment..."
python3.10 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install MediaPipe (compatible version)
echo "📦 Installing MediaPipe 0.10.9..."
pip install mediapipe==0.10.9

# Install main dependencies
echo "📦 Installing core dependencies..."
pip install opencv-python numpy pyautogui pyttsx3

# Optional OpenAI
echo "📦 Installing OpenAI (optional)..."
pip install openai || true

# Install web app dependencies
echo "🌐 Installing web app dependencies..."
cd web_app || exit
pip install -r requirements.txt
cd ..

# Verify MediaPipe
echo "✅ Verifying MediaPipe..."
python - <<EOF
import mediapipe as mp
print("MediaPipe version:", mp.__version__)
print("solutions exists:", hasattr(mp, "solutions"))
EOF

echo "🎉 SETUP COMPLETE"
echo "▶️ Run the app using: python app.py"

