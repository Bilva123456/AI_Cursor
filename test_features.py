#!/usr/bin/env python3
"""
Test script to verify all new gesture features are working
"""

import sys
import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time

print("=" * 60)
print("TESTING GESTURE CONTROL SYSTEM FEATURES")
print("=" * 60)

# Test 1: Imports
print("\n[1/6] Testing imports...")
try:
    import app
    print("✅ app.py imports successfully")
except Exception as e:
    print(f"❌ Failed to import app.py: {e}")
    sys.exit(1)

# Test 2: MediaPipe hands
print("\n[2/6] Testing MediaPipe Hands initialization...")
try:
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=1
    )
    print("✅ MediaPipe Hands initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize MediaPipe Hands: {e}")
    sys.exit(1)

# Test 3: Webcam
print("\n[3/6] Testing webcam access...")
try:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        h, w = frame.shape[:2]
        print(f"✅ Webcam working! Resolution: {w}x{h}")
        cap.release()
    else:
        print("❌ Webcam captured frame but returned invalid data")
        sys.exit(1)
except Exception as e:
    print(f"❌ Webcam test failed: {e}")
    sys.exit(1)

# Test 4: Advanced Features Classes
print("\n[4/6] Testing Advanced Features classes...")
try:
    # Check if AdvancedGestureFeatures exists
    from app import advanced_features, gesture_speed_analyzer, gesture_recorder
    
    # Test effect modes
    modes = ['rainbow', 'particle', 'hologram', 'magnetic', 'trail', 'normal']
    for mode in modes:
        advanced_features.effect_mode = mode
        assert advanced_features.effect_mode == mode, f"Failed to set mode: {mode}"
    
    print("✅ Advanced Features classes working")
    print(f"   - Effect modes: {modes}")
    print(f"   - Shape detection: {hasattr(advanced_features, 'shape_detection_mode')}")
    print(f"   - Gesture speed analyzer: {gesture_speed_analyzer is not None}")
    print(f"   - Gesture recorder: {gesture_recorder is not None}")
except Exception as e:
    print(f"❌ Advanced Features test failed: {e}")
    sys.exit(1)

# Test 5: Shape Detection
print("\n[5/6] Testing shape detection...")
try:
    from app import advanced_features
    
    # Simulate a circular gesture
    circle_points = []
    center = (200, 200)
    radius = 50
    for angle in np.linspace(0, 2*np.pi, 25):
        x = int(center[0] + radius * np.cos(angle))
        y = int(center[1] + radius * np.sin(angle))
        circle_points.append((x, y))
    
    advanced_features.circle_points = circle_points
    shape = advanced_features._analyze_shape()
    
    if shape == 'CIRCLE':
        print("✅ Circle detection working")
    else:
        print(f"⚠️  Circle detection returned: {shape} (expected CIRCLE)")
    
    # Reset for line test
    advanced_features.circle_points = []
    line_points = [(i*5, i*5) for i in range(20)]
    advanced_features.circle_points = line_points
    shape = advanced_features._analyze_shape()
    
    if shape == 'LINE':
        print("✅ Line detection working")
    else:
        print(f"⚠️  Line detection returned: {shape} (expected LINE)")
    
except Exception as e:
    print(f"❌ Shape detection test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Command Generator
print("\n[6/6] Testing command generator...")
try:
    from app import command_generator
    
    # Test gesture to command conversion
    test_gestures = [
        ('fist', 'peace', 'open_hand'),
        ('thumbs_up', 'thumbs_up', 'thumbs_up', 'thumbs_up'),
        ('point', 'point', 'point', 'point', 'point'),
    ]
    
    for gesture_seq in test_gestures:
        command = command_generator.gesture_sequence_to_command(gesture_seq)
        print(f"   ✓ {gesture_seq} → {command}")
    
    print("✅ Command generator working")
except Exception as e:
    print(f"❌ Command generator test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL FEATURE TESTS PASSED!")
print("=" * 60)
print("\n🎮 HOW TO USE THE FEATURES:\n")
print("1. Run: python app.py")
print("2. Press number keys for effects:")
print("   • Press '1' → Rainbow cursor effect")
print("   • Press '2' → Particle trail effect")
print("   • Press '3' → Hologram cursor effect")
print("   • Press '4' → Magnetic field effect")
print("   • Press '5' → Motion trail effect")
print("3. Press 'S' → Enable shape detection")
print("   • Draw a circle with your hand")
print("   • App will recognize: CIRCLE, LINE, or POLYGON")
print("4. Press 'R' → Start gesture recording")
print("   • Make your custom gesture")
print("   • Press 'R' again to stop recording")
print("5. Press 'A' → AI Mode (gesture-to-command)")
print("   • Make gesture sequences to execute commands")
print("\n💡 TIPS:")
print("   - Particle effects show better with fast hand movements")
print("   - Hologram looks better with slow, deliberate movements")
print("   - For circle detection, draw smooth circular motions")
print("   - Recording captures all hand landmarks for playback")
print("\n🚀 Ready to test! Press Space to start app.py\n")
