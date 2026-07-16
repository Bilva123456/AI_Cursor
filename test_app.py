#!/usr/bin/env python3
"""Quick test to verify the app initializes correctly"""

import sys
import io

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("GESTURE CONTROL APP - INITIALIZATION TEST")
print("=" * 60)

# Test imports
print("\n1. Testing imports...")
try:
    import cv2
    print("✓ OpenCV imported")
except Exception as e:
    print(f"✗ OpenCV failed: {e}")
    sys.exit(1)

try:
    import mediapipe as mp
    print("✓ MediaPipe imported")
except Exception as e:
    print(f"✗ MediaPipe failed: {e}")
    sys.exit(1)

try:
    mp_hands = mp.solutions.hands
    print("✓ MediaPipe.solutions.hands loaded")
except Exception as e:
    print(f"✗ MediaPipe.solutions failed: {e}")
    sys.exit(1)

# Test webcam
print("\n2. Testing webcam...")
try:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        print(f"✓ Webcam detected (resolution: {frame.shape[1]}x{frame.shape[0]})")
        cap.release()
    else:
        print("✗ Webcam not responding")
        sys.exit(1)
except Exception as e:
    print(f"✗ Webcam test failed: {e}")
    sys.exit(1)

# Test MediaPipe initialization
print("\n3. Testing MediaPipe Hands initialization...")
try:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=1
    )
    print("✓ MediaPipe Hands model loaded successfully")
    cap.release()
except Exception as e:
    print(f"✗ MediaPipe Hands initialization failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nYour app is ready to run!")
print("Start it with: python app.py")
print("\nKeybinds:")
print("  A - AI Mode")
print("  C - Cursor Mode")
print("  1-6 - Visual effects")
print("  S - Shape detection")
print("  R - Record gesture")
print("  ESC - Exit")
print("\n" + "=" * 60)
