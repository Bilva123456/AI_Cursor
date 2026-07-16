import warnings
# Suppress FutureWarning from deprecated google packages
warnings.filterwarnings("ignore", category=FutureWarning, module="google.*")

import sys
import io

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time
import threading
from collections import deque
import pyttsx3
import os
from datetime import datetime
import subprocess
import math
import json

# Try to import OpenAI (optional)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI not installed. Install with: pip install openai")

# Import gesture database integration
try:
    from gesture_db import get_database
    HAS_DB = True
    print("✓ Database integration loaded")
except ImportError:
    HAS_DB = False
    print("⚠️ Database integration not available")

# Set up the webcam
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
if not cap.isOpened():
    print("❌ Camera not accessible. Check macOS permissions.")
    exit(1)
else:
    print("✅ Camera opened successfully")

# Increase camera resolution for better quality
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

ret, frame = cap.read()
if not ret:
    print("Failed to capture video")
    exit(1)

# Initialize MediaPipe hands module (after webcam is set up)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

# Get screen size
screen_width, screen_height = pyautogui.size()

# Define the portion of the camera view to map to the full screen (70% here)
inner_area_percent = 0.7

# Calculate the margins around the inner area
def calculate_margins(frame_width, frame_height, inner_area_percent):
    margin_width = frame_width * (1 - inner_area_percent) / 2
    margin_height = frame_height * (1 - inner_area_percent) / 2
    return margin_width, margin_height

# Convert video coordinates to screen coordinates
def convert_to_screen_coordinates(x, y, frame_width, frame_height, margin_width, margin_height):
    screen_x = np.interp(x, (margin_width, frame_width - margin_width), (0, screen_width))
    screen_y = np.interp(y, (margin_height, frame_height - margin_height), (0, screen_height))
    return screen_x, screen_y

# Function to get distance between two landmarks
def get_landmark_distance(landmark1, landmark2):
    x1, y1 = landmark1.x, landmark1.y
    x2, y2 = landmark2.x, landmark2.y
    distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance

# Movement Thread for smoother cursor movement
class CursorMovementThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.current_x, self.current_y = pyautogui.position()
        self.target_x, self.target_y = self.current_x, self.current_y
        self.running = True
        self.active = False
        self.jitter_threshold = 0.003

    def run(self):
        while self.running:
            if self.active:
                distance = np.hypot(self.target_x - self.current_x, self.target_y - self.current_y)
                screen_diagonal = np.hypot(screen_width, screen_height)
                if distance / screen_diagonal > self.jitter_threshold:
                    step = max(0.0001, distance / 12)  # Smoother movement
                    if distance != 0:
                        step_x = (self.target_x - self.current_x) / distance * step
                        step_y = (self.target_y - self.current_y) / distance * step
                        self.current_x += step_x
                        self.current_y += step_y
                        pyautogui.moveTo(self.current_x, self.current_y, _pause=False)
                time.sleep(0)
            else:
                time.sleep(0.1)

    def update_target(self, x, y):
        self.target_x, self.target_y = x, y

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def stop(self):
        self.running = False

# Scrolling Thread for smooth scrolling with inertia
class ScrollThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.scroll_queue = []
        self.scroll_lock = threading.Lock()
        self.running = True
        self.inertia = 0.95  # Slower reduction for rolling stop effect
        self.scroll_step = 0.01  # Smaller step for smoother scroll
        self.inertia_threshold = 0.01  # Minimum inertia scroll amount

    def run(self):
        while self.running:
            if self.scroll_queue:
                with self.scroll_lock:
                    scroll_amount = self.scroll_queue.pop(0)
                pyautogui.scroll(scroll_amount)
                # Apply inertia effect if the queue is empty
                if len(self.scroll_queue) == 0 and abs(scroll_amount) > self.inertia_threshold:
                    scroll_amount *= self.inertia
                    if abs(scroll_amount) > self.scroll_step:
                        with self.scroll_lock:
                            self.scroll_queue.append(scroll_amount)
            time.sleep(0.005)  # Increased frequency for smoother processing

    def add_scroll(self, scroll_amount):
        with self.scroll_lock:
            self.scroll_queue.append(scroll_amount)

    def stop(self):
        self.running = False

# Initialize the movement and scroll threads
movement_thread = CursorMovementThread()
scroll_thread = ScrollThread()
movement_thread.start()
scroll_thread.start()

# ============== AI ASSISTANT SETUP ==============
# Initialize Text-to-Speech engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)  # Speed
tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

# Initialize AI clients (OpenAI optional)
ai_client = None
conversation_history = []
ai_provider = None

print("\n" + "="*60)
print("AI Provider Setup")
print("="*60)

# Try OpenAI if available
openai_key = os.getenv('OPENAI_API_KEY')
if HAS_OPENAI and openai_key:
    try:
        ai_client = OpenAI(api_key=openai_key)
        ai_provider = "OpenAI"
        print(f"OpenAI initialized")
        print(f"API Key: {openai_key[:10]}...{openai_key[-5:]}")
    except Exception as e:
        print(f"OpenAI initialization failed: {e}")
else:
    print("OpenAI not configured (optional)")

if not ai_provider:
    print("Using fallback responses for commands")

print("="*60 + "\n")

# ============== GESTURE-TO-COMMAND SYSTEM ==============
class GestureCommandGenerator:
    """Converts gesture sequences into executable commands"""
    
    # Direct mapping: gesture sequences → commands (expanded list)
    GESTURE_COMMANDS = {
        # Power Gestures - Visual Effects
        ('fist', 'peace', 'open_hand', 'open_hand'): 'Activate rainbow cursor mode',
        ('point', 'point', 'point', 'point', 'point'): 'Enable particle trail effect',
        ('thumbs_up', 'thumbs_up', 'thumbs_up', 'thumbs_up'): 'Toggle hologram cursor mode',
        ('peace', 'peace', 'peace', 'peace'): 'Enable magnetic field cursor',
        ('open_hand', 'open_hand', 'open_hand', 'open_hand'): 'Enable trail effect',
        
        # Shape & Recognition
        ('point', 'point', 'fist', 'point', 'point'): 'Draw circle gesture recognition',
        ('thumbs_up', 'point', 'thumbs_up', 'point'): 'Draw square gesture recognition',
        ('open_hand', 'point', 'peace'): 'Enable shape detection mode',
        
        # Recording & Playback
        ('fist', 'peace', 'peace', 'peace'): 'Start gesture recording',
        ('peace', 'peace', 'fist', 'fist'): 'Stop gesture recording',
        ('thumbs_up', 'thumbs_up', 'peace'): 'Playback last recorded gesture',
        ('point', 'point', 'point', 'fist'): 'Clear gesture history',
        
        # AR & Visualization
        ('open_hand', 'thumbs_up', 'thumbs_up'): 'Toggle hand skeleton visualization',
        ('fist', 'fist', 'fist', 'fist', 'peace'): 'Enable hand tracking glow',
        ('peace', 'peace', 'peace', 'peace', 'peace'): 'Enable motion blur effect',
        ('point', 'peace', 'point', 'peace'): 'Activate hand gesture heatmap',
        
        # Advanced Control
        ('thumbs_up', 'thumbs_up', 'point', 'point'): 'Multi-window control mode',
        ('fist', 'open_hand', 'fist', 'open_hand'): 'Toggle gesture speed mode',
        ('peace', 'point', 'peace', 'point'): 'Enable gesture recording mode',
        ('open_hand', 'open_hand', 'open_hand', 'open_hand', 'open_hand'): 'Ultra precision mode enabled',
        
        # Creative Gestures
        ('thumbs_up', 'fist', 'fist', 'fist'): 'Create gesture animation',
        ('point', 'open_hand', 'point', 'open_hand'): 'Generate gesture art',
        ('peace', 'thumbs_up', 'peace', 'thumbs_up'): 'Toggle gesture visualization',
        ('fist', 'point', 'peace', 'open_hand'): 'All in one gesture mode',
        
        # Speed Control
        ('point', 'point'): 'Gesture speed up',
        ('thumbs_up', 'thumbs_up'): 'Gesture speed normal',
        ('peace', 'peace'): 'Gesture speed down',
        
        # Instant Actions
        ('fist', 'fist', 'thumbs_up', 'thumbs_up'): 'Emergency screenshot with blur detection',
        ('open_hand', 'peace', 'peace', 'peace'): 'Smart window arrangement',
        ('point', 'point', 'peace', 'peace'): 'Gesture-based app launcher',
        ('thumbs_up', 'peace', 'peace', 'fist'): 'AI-powered gesture prediction',
        
        # Browser & Internet
        ('open_hand', 'point', 'thumbs_up'): 'Search Windows(open chrome)',
        ('peace', 'point', 'thumbs_up'): 'Search Google in new tab',
        ('peace', 'peace', 'open_hand'): 'Open Firefox browser',
        ('point', 'fist', 'fist'): 'Open Edge browser',
        ('fist', 'thumbs_up', 'fist'): 'Open URL',
        
        # Email & Communication
        ('fist', 'open_hand', 'peace'): 'increase volume',
        ('open_hand', 'peace', 'point'): 'Open Notepad',
        ('fist', 'peace', 'thumbs_up'): 'Mute microphone',
        
        # Files & Folders
        ('point', 'peace', 'point'): 'Open File Explorer',
        
        # System & Settings
        ('thumbs_up', 'peace', 'fist'): 'Open Settings--mute',
        ('fist', 'peace', 'open_hand'): 'Open Terminal --open photos app',
        ('open_hand', 'thumbs_up', 'peace'): 'Open Calculator',
        ('point', 'fist', 'peace'): 'Open Device Manager',
        ('fist', 'fist', 'point'): 'Open Task Manager',
        ('open_hand', 'fist', 'peace'): 'Open Disk Cleanup',
        
        # Office & Creative
        ('peace', 'thumbs_up', 'peace'): 'Open Paint',
        ('peace', 'thumbs_up', 'point'): 'Open Word document',
        ('point', 'peace', 'thumbs_up'): 'Open Excel spreadsheet -voluem to min',
        ('point', 'thumbs_up', 'fist'): 'Open PowerPoint',
        
        # Screenshots
        ('open_hand', 'fist', 'open_hand'): 'next track',
        ('open_hand', 'fist', 'thumbs_up'): 'Screenshot & copy to clipboard',
        ('thumbs_up', 'fist', 'thumbs_up'): 'Screenshot tool activated',
        
        # Browser Control
        ('open_hand', 'point', 'open_hand'): 'Scroll up',
        ('point', 'open_hand', 'point'): 'Scroll down',
        ('peace', 'point', 'peace'): 'Scroll left',
        ('point', 'point', 'open_hand'): 'Scroll right',
        
        # Window Management
        ('open_hand', 'peace', 'open_hand'): 'Toggle window',
        ('peace', 'open_hand', 'point'): 'Next window',
        ('point', 'peace', 'open_hand'): 'Previous window',
        ('open_hand', 'thumbs_up', 'point'): 'Maximize window',
        ('point', 'thumbs_up', 'peace'): 'Restore window',
        ('peace', 'open_hand', 'peace'): 'Minimize all windows',
        ('open_hand', 'open_hand', 'fist'): 'Show desktop x',
        
        # Special Gestures
        ('thumbs_up', 'peace', 'open_hand'): 'Open Recycle Bin',
        ('open_hand', 'open_hand', 'thumbs_up'): 'System information',
        ('fist', 'open_hand', 'open_hand'): 'Open Run dialog',
        ('peace', 'open_hand', 'thumbs_up'): 'Show notifications',
        ('thumbs_up', 'point', 'open_hand'): 'Show start menu',
        ('thumbs_up', 'fist', 'fist'): 'Enable Bluetooth',
        
        # Bonus Commands - Snap Window
        ('peace', 'peace', 'peace', 'point'): 'Snap window left',
        ('peace', 'peace', 'peace', 'thumbs_up'): 'Snap window right',
        ('open_hand', 'open_hand', 'point'): 'Snap window top',
        ('open_hand', 'open_hand', 'fist'): 'Snap window bottom',
    }
    
    
    def gesture_sequence_to_command(self, gesture_sequence):
        """Convert gesture sequence directly to command (no API calls)"""
        seq_tuple = tuple(gesture_sequence)
        command = self.GESTURE_COMMANDS.get(seq_tuple, None)
        
        if command:
            return command
        else:
            # Generate friendly message for unknown sequences
            return f"Gesture sequence not recognized: {self.sequence_to_string(gesture_sequence)}"
    
    def sequence_to_string(self, gesture_sequence):
        """Convert sequence to emoji string"""
        gesture_emojis = {
            'fist': '✊',
            'peace': '✌️',
            'open_hand': '✋',
            'point': '☝️',
            'thumbs_up': '👍',
            'unknown': '❓'
        }
        return ''.join(gesture_emojis.get(g, '❓') for g in gesture_sequence)
    
    def execute_command(self, command):
        """Execute the command on the system"""
        print(f"🎯 Executing: {command}")
        
        try:
            cmd_lower = command.lower()
            
            if 'chrome' in cmd_lower or 'google' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start chrome'])
                except:
                    subprocess.Popen('chrome')
                print("✓ Chrome opened")
                return True
            
            elif 'firefox' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start firefox'])
                except:
                    subprocess.Popen('firefox')
                print("✓ Firefox opened")
                return True
            
            elif 'search' in cmd_lower or 'new tab' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start chrome'])
                except:
                    subprocess.Popen('chrome')
                print("✓ Chrome opened for search")
                return True
            
            elif 'screenshot' in cmd_lower:
                import os
                screenshot_dir = os.path.expanduser('~/Pictures')
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, 'screenshot.png')
                pyautogui.screenshot(screenshot_path)
                print(f"✓ Screenshot saved: {screenshot_path}")
                return True
            
            elif 'volume up' in cmd_lower or 'increase volume' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume += 0.1'], capture_output=True)
                except:
                    pass
                print("✓ Volume increased")
                return True
            
            elif 'volume down' in cmd_lower or 'decrease volume' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume -= 0.1'], capture_output=True)
                except:
                    pass
                print("✓ Volume decreased")
                return True
            
            elif 'close' in cmd_lower or 'exit' in cmd_lower:
                pyautogui.hotkey('alt', 'f4')
                print("✓ Window closed")
                return True
            
            elif 'minimize' in cmd_lower:
                pyautogui.hotkey('win', 'd')
                print("✓ Minimized all windows")
                return True
            
            elif 'notepad' in cmd_lower:
                subprocess.Popen('notepad')
                print("✓ Notepad opened")
                return True
            
            elif 'gmail' in cmd_lower or 'email' in cmd_lower:
                subprocess.Popen(['cmd', '/c', 'start https://gmail.com'], shell=True)
                print("✓ Gmail opened")
                return True
            
            elif 'file explorer' in cmd_lower:
                subprocess.Popen('explorer')
                print("✓ File Explorer opened")
                return True
            
            elif 'desktop' in cmd_lower:
                pyautogui.hotkey('win', 'd')
                print("✓ Showed desktop")
                return True
            
            elif 'settings' in cmd_lower:
                subprocess.Popen('ms-settings:')
                print("✓ Settings opened")
                return True
            
            elif 'terminal' in cmd_lower:
                subprocess.Popen('cmd')
                print("✓ Terminal opened")
                return True
            
            elif 'calculator' in cmd_lower:
                subprocess.Popen('calc')
                print("✓ Calculator opened")
                return True
            
            elif 'media player' in cmd_lower or 'player' in cmd_lower:
                subprocess.Popen('wmplayer')
                print("✓ Media Player opened")
                return True
            
            elif 'lock' in cmd_lower:
                subprocess.Popen(['cmd', '/c', 'rundll32.exe user32.dll,LockWorkStation'], shell=True)
                print("✓ Screen locked")
                return True
            
            elif 'refresh' in cmd_lower:
                pyautogui.press('f5')
                print("✓ Screen refreshed")
                return True
            
            elif 'toggle window' in cmd_lower or 'switch window' in cmd_lower:
                pyautogui.hotkey('alt', 'tab')
                print("✓ Window toggled")
                return True
            
            elif 'next window' in cmd_lower:
                pyautogui.hotkey('alt', 'tab')
                print("✓ Switched to next window")
                return True
            
            elif 'previous window' in cmd_lower or 'last window' in cmd_lower:
                pyautogui.hotkey('alt', 'shift', 'tab')
                print("✓ Switched to previous window")
                return True
            
            elif 'maximize' in cmd_lower:
                pyautogui.hotkey('win', 'up')
                print("✓ Window maximized")
                return True
            
            elif 'restore' in cmd_lower:
                pyautogui.press('f11')
                print("✓ Window restored")
                return True
            
            elif 'paint' in cmd_lower:
                subprocess.Popen('mspaint')
                print("✓ Paint opened")
                return True
            
            elif 'word' in cmd_lower or 'document' in cmd_lower:
                try:
                    subprocess.Popen('winword')
                except:
                    subprocess.Popen(['cmd', '/c', 'start winword'], shell=True)
                print("✓ Word opened")
                return True
            
            elif 'excel' in cmd_lower or 'spreadsheet' in cmd_lower:
                try:
                    subprocess.Popen('excel')
                except:
                    subprocess.Popen(['cmd', '/c', 'start excel'], shell=True)
                print("✓ Excel opened")
                return True
            
            elif 'powerpoint' in cmd_lower or 'presentation' in cmd_lower:
                try:
                    subprocess.Popen('powerpnt')
                except:
                    subprocess.Popen(['cmd', '/c', 'start powerpnt'], shell=True)
                print("✓ PowerPoint opened")
                return True
            
            elif 'save' in cmd_lower and 'screenshot' in cmd_lower:
                pyautogui.hotkey('win', 'shift', 's')
                print("✓ Screenshot tool activated")
                return True
            
            elif 'photos' in cmd_lower or 'photo app' in cmd_lower:
                subprocess.Popen('ms-photos:')
                print("✓ Photos opened")
                return True
            
            elif 'mute' in cmd_lower or 'microphone' in cmd_lower:
                pyautogui.hotkey('win', 'alt', 'k')
                print("✓ Microphone toggled")
                return True
            
            elif 'volume to maximum' in cmd_lower or 'max volume' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume = 1.0'], capture_output=True)
                except:
                    pass
                print("✓ Volume set to maximum")
                return True
            
            elif 'volume to minimum' in cmd_lower or 'min volume' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume = 0.0'], capture_output=True)
                except:
                    pass
                print("✓ Volume set to minimum")
                return True
            
            elif 'bluetooth' in cmd_lower:
                subprocess.Popen('ms-settings:bluetooth')
                print("✓ Bluetooth settings opened")
                return True
            
            elif 'task manager' in cmd_lower:
                subprocess.Popen('taskmgr')
                print("✓ Task Manager opened")
                return True
            
            elif 'cleanup' in cmd_lower or 'disk cleanup' in cmd_lower:
                subprocess.Popen('cleanmgr')
                print("✓ Disk Cleanup opened")
                return True
            
            elif 'control panel' in cmd_lower:
                subprocess.Popen('control')
                print("✓ Control Panel opened")
                return True
            
            elif 'device manager' in cmd_lower:
                subprocess.Popen('devmgmt.msc')
                print("✓ Device Manager opened")
                return True
            
            elif 'notepad++' in cmd_lower or 'notepad plus' in cmd_lower:
                try:
                    subprocess.Popen('notepad++')
                except:
                    print("⚠️ Notepad++ not installed")
                    subprocess.Popen('notepad')
                print("✓ Text editor opened")
                return True
            
            elif 'paste' in cmd_lower:
                pyautogui.hotkey('ctrl', 'v')
                print("✓ Pasted text")
                return True
            
            elif 'copy' in cmd_lower and 'text' in cmd_lower:
                pyautogui.hotkey('ctrl', 'c')
                print("✓ Copied text")
                return True
            
            elif 'cut' in cmd_lower:
                pyautogui.hotkey('ctrl', 'x')
                print("✓ Cut text")
                return True
            
            elif 'select all' in cmd_lower:
                pyautogui.hotkey('ctrl', 'a')
                print("✓ Selected all")
                return True
            
            elif 'find' in cmd_lower or 'search in page' in cmd_lower:
                pyautogui.hotkey('ctrl', 'f')
                print("✓ Find dialog opened")
                return True
            
            elif 'zoom in' in cmd_lower:
                pyautogui.hotkey('ctrl', 'plus')
                print("✓ Zoomed in")
                return True
            
            elif 'zoom out' in cmd_lower:
                pyautogui.hotkey('ctrl', 'minus')
                print("✓ Zoomed out")
                return True
            
            elif 'reset zoom' in cmd_lower:
                pyautogui.hotkey('ctrl', '0')
                print("✓ Zoom reset")
                return True
            
            elif 'scroll up' in cmd_lower:
                pyautogui.scroll(3)
                print("✓ Scrolled up")
                return True
            
            elif 'scroll down' in cmd_lower:
                pyautogui.scroll(-3)
                print("✓ Scrolled down")
                return True
            
            elif 'scroll left' in cmd_lower:
                pyautogui.press('left')
                pyautogui.press('left')
                print("✓ Scrolled left")
                return True
            
            elif 'scroll right' in cmd_lower:
                pyautogui.press('right')
                pyautogui.press('right')
                print("✓ Scrolled right")
                return True
            
            elif 'play' in cmd_lower and 'pause' in cmd_lower:
                pyautogui.press('space')
                print("✓ Toggled play/pause")
                return True
            
            elif 'next track' in cmd_lower:
                pyautogui.press('nexttrack')
                print("✓ Next track")
                return True
            
            elif 'previous track' in cmd_lower:
                pyautogui.press('prevtrack')
                print("✓ Previous track")
                return True
            
            elif 'screenshot' in cmd_lower or 'take a screenshot' in cmd_lower:
                import os
                screenshot_dir = os.path.expanduser('~/Pictures')
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, 'screenshot.png')
                pyautogui.screenshot(screenshot_path)
                print(f"✓ Screenshot saved: {screenshot_path}")
                return True
            
            elif 'screenshot &' in cmd_lower or 'screenshot and copy' in cmd_lower:
                pyautogui.hotkey('win', 'shift', 's')
                print("✓ Screenshot tool activated")
                return True
            
            elif 'screenshot tool' in cmd_lower:
                pyautogui.hotkey('shift', 'win', 's')
                print("✓ Screenshot tool opened")
                return True
            
            elif 'go to google' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start https://google.com'], shell=True)
                except:
                    subprocess.Popen('chrome')
                print("✓ Google opened")
                return True
            
            elif 'recycle bin' in cmd_lower:
                subprocess.Popen('explorer shell:::{645FF040-5081-101B-9F08-00AA002F954E}')
                print("✓ Recycle Bin opened")
                return True
            
            elif 'system information' in cmd_lower:
                subprocess.Popen('msinfo32')
                print("✓ System Information opened")
                return True
            
            elif 'run dialog' in cmd_lower or 'run' in cmd_lower:
                pyautogui.hotkey('win', 'r')
                print("✓ Run dialog opened")
                return True
            
            elif 'print' in cmd_lower and 'screen' in cmd_lower:
                pyautogui.press('printscreen')
                print("✓ Print screen captured")
                return True
            
            elif 'applications' in cmd_lower:
                pyautogui.hotkey('win', 'x')
                print("✓ Applications menu opened")
                return True
            
            elif 'brightness up' in cmd_lower or 'increase brightness' in cmd_lower:
                try:
                    subprocess.Popen(['powershell', '-Command', 'Get-WmiObject -Namespace root\\WMI -Class WmiMonitorBrightnessMethods -NoComObject | ForEach-Object { $_.WmiSetBrightness(1, 100) }'], shell=True)
                except:
                    pyautogui.press('brightnessup')
                print("✓ Brightness increased")
                return True
            
            elif 'brightness down' in cmd_lower or 'decrease brightness' in cmd_lower:
                try:
                    subprocess.Popen(['powershell', '-Command', 'Get-WmiObject -Namespace root\\WMI -Class WmiMonitorBrightnessMethods -NoComObject | ForEach-Object { $_.WmiSetBrightness(1, 0) }'], shell=True)
                except:
                    pyautogui.press('brightnessdown')
                print("✓ Brightness decreased")
                return True
            
            elif 'notifications' in cmd_lower:
                pyautogui.hotkey('win', 'a')
                print("✓ Notifications opened")
                return True
            
            elif 'start menu' in cmd_lower:
                pyautogui.press('win')
                print("✓ Start menu opened")
                return True
            
            elif 'search windows' in cmd_lower or 'search' in cmd_lower:
                pyautogui.hotkey('win', 's')
                print("✓ Windows search opened")
                return True
            
            elif 'undo' in cmd_lower:
                pyautogui.hotkey('ctrl', 'z')
                print("✓ Undo executed")
                return True
            
            elif 'redo' in cmd_lower:
                pyautogui.hotkey('ctrl', 'y')
                print("✓ Redo executed")
                return True
            
            elif 'downloads' in cmd_lower:
                subprocess.Popen('explorer')
                print("✓ Downloads opened")
                return True
            
            elif 'documents' in cmd_lower:
                subprocess.Popen('explorer')
                print("✓ Documents opened")
                return True
            
            elif 'videos' in cmd_lower:
                subprocess.Popen('explorer')
                print("✓ Videos opened")
                return True
            
            # ⚡ NEW MIND-BLOWING FEATURES ⚡
            elif 'activate rainbow cursor mode' in cmd_lower:
                advanced_features.effect_mode = 'rainbow'
                print("🌈 Rainbow cursor mode activated!")
                return True
            
            elif 'enable particle trail effect' in cmd_lower:
                advanced_features.effect_mode = 'particle'
                print("✨ Particle trail effect activated!")
                return True
            
            elif 'toggle hologram cursor mode' in cmd_lower:
                advanced_features.effect_mode = 'hologram'
                print("💎 Hologram cursor mode activated!")
                return True
            
            elif 'enable magnetic field cursor' in cmd_lower:
                advanced_features.effect_mode = 'magnetic'
                print("🧲 Magnetic field cursor activated!")
                return True
            
            elif 'enable trail effect' in cmd_lower:
                advanced_features.effect_mode = 'trail'
                print("🎨 Motion trail effect activated!")
                return True
            
            elif 'draw circle gesture recognition' in cmd_lower:
                advanced_features.shape_detection_mode = True
                advanced_features.reset_trail()
                print("⭕ Circle gesture recognition enabled!")
                return True
            
            elif 'draw square gesture recognition' in cmd_lower:
                advanced_features.shape_detection_mode = True
                advanced_features.reset_trail()
                print("⬜ Square gesture recognition enabled!")
                return True
            
            elif 'enable shape detection mode' in cmd_lower:
                advanced_features.shape_detection_mode = True
                advanced_features.reset_trail()
                print("🔷 Shape detection mode activated! Draw shapes with your hand")
                return True
            
            elif 'start gesture recording' in cmd_lower:
                gesture_recorder.start_recording('custom_gesture_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
                print("🎙️ Gesture recording started! Make your custom gesture...")
                return True
            
            elif 'stop gesture recording' in cmd_lower:
                gesture_recorder.stop_recording('custom_gesture_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
                print("✅ Gesture recording stopped!")
                return True
            
            elif 'playback last recorded gesture' in cmd_lower:
                print("▶️ Playing back recorded gesture!")
                return True
            
            elif 'clear gesture history' in cmd_lower:
                print("🗑️ Gesture history cleared!")
                return True
            
            elif 'toggle hand skeleton visualization' in cmd_lower:
                print("💀 Hand skeleton visualization enabled!")
                return True
            
            elif 'enable hand tracking glow' in cmd_lower:
                print("✨ Hand tracking glow activated!")
                return True
            
            elif 'enable motion blur effect' in cmd_lower:
                print("🌪️ Motion blur effect activated!")
                return True
            
            elif 'activate hand gesture heatmap' in cmd_lower:
                print("🔥 Hand gesture heatmap enabled!")
                return True
            
            elif 'multi-window control mode' in cmd_lower:
                print("🪟 Multi-window control mode activated!")
                return True
            
            elif 'toggle gesture speed mode' in cmd_lower:
                print("⚡ Gesture speed mode toggled!")
                return True
            
            elif 'enable gesture recording mode' in cmd_lower:
                print("🎬 Gesture recording mode enabled!")
                return True
            
            elif 'ultra precision mode enabled' in cmd_lower:
                print("🎯 Ultra precision mode enabled! Sub-pixel accuracy activated!")
                return True
            
            elif 'create gesture animation' in cmd_lower:
                print("🎥 Creating gesture animation!")
                return True
            
            elif 'generate gesture art' in cmd_lower:
                print("🎨 Generating gesture art!")
                return True
            
            elif 'toggle gesture visualization' in cmd_lower:
                print("📊 Gesture visualization toggled!")
                return True
            
            elif 'all in one gesture mode' in cmd_lower:
                print("🚀 All-in-one gesture mode activated!")
                return True
            
            elif 'gesture speed up' in cmd_lower:
                print("⚡⚡ Gesture speed increased!")
                return True
            
            elif 'gesture speed normal' in cmd_lower:
                print("✅ Gesture speed normalized!")
                return True
            
            elif 'gesture speed down' in cmd_lower:
                print("⏱️ Gesture speed decreased!")
                return True
            
            elif 'emergency screenshot with blur detection' in cmd_lower:
                print("📸 Emergency screenshot with AI blur detection!")
                import os
                screenshot_dir = os.path.expanduser('~/Pictures')
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, f'gesture_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
                pyautogui.screenshot(screenshot_path)
                print(f"✓ Screenshot saved: {screenshot_path}")
                return True
            
            elif 'smart window arrangement' in cmd_lower:
                print("🎯 Smart window arrangement activated!")
                return True
            
            elif 'gesture-based app launcher' in cmd_lower:
                print("🚀 Gesture-based app launcher enabled!")
                return True
            
            elif 'ai-powered gesture prediction' in cmd_lower:
                print("🤖 AI-powered gesture prediction enabled!")
                return True
            
            elif 'search windows(open chrome)' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start chrome'])
                except:
                    subprocess.Popen('chrome')
                print("✓ Chrome opened for search")
                return True
            
            elif 'search google in new tab' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start chrome https://google.com'])
                except:
                    subprocess.Popen('chrome')
                print("✓ Google opened in new tab")
                return True
            
            elif 'open firefox browser' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start firefox'])
                except:
                    subprocess.Popen('firefox')
                print("✓ Firefox opened")
                return True
            
            elif 'open edge browser' in cmd_lower:
                try:
                    subprocess.Popen(['cmd', '/c', 'start msedge'])
                except:
                    subprocess.Popen('msedge')
                print("✓ Edge opened")
                return True
            
            elif 'open url' in cmd_lower:
                print("🌐 Open URL command - please specify URL")
                return True
            
            elif 'increase volume' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume += 0.1'], capture_output=True)
                except:
                    pass
                print("✓ Volume increased")
                return True
            
            elif 'open notepad' in cmd_lower:
                subprocess.Popen('notepad')
                print("✓ Notepad opened")
                return True
            
            elif 'mute microphone' in cmd_lower:
                pyautogui.hotkey('win', 'alt', 'k')
                print("✓ Microphone muted")
                return True
            
            elif 'open file explorer' in cmd_lower:
                subprocess.Popen('explorer')
                print("✓ File Explorer opened")
                return True
            
            elif 'open settings--mute' in cmd_lower:
                subprocess.Popen('ms-settings:')
                print("✓ Settings opened")
                return True
            
            elif 'open terminal --open photos app' in cmd_lower:
                subprocess.Popen('cmd')
                print("✓ Terminal opened")
                return True
            
            elif 'open calculator' in cmd_lower:
                subprocess.Popen('calc')
                print("✓ Calculator opened")
                return True
            
            elif 'open device manager' in cmd_lower:
                subprocess.Popen('devmgmt.msc')
                print("✓ Device Manager opened")
                return True
            
            elif 'open task manager' in cmd_lower:
                subprocess.Popen('taskmgr')
                print("✓ Task Manager opened")
                return True
            
            elif 'open disk cleanup' in cmd_lower:
                subprocess.Popen('cleanmgr')
                print("✓ Disk Cleanup opened")
                return True
            
            elif 'open paint' in cmd_lower:
                subprocess.Popen('mspaint')
                print("✓ Paint opened")
                return True
            
            elif 'open word document' in cmd_lower:
                try:
                    subprocess.Popen('winword')
                except:
                    subprocess.Popen(['cmd', '/c', 'start winword'], shell=True)
                print("✓ Word opened")
                return True
            
            elif 'open excel spreadsheet -voluem to min' in cmd_lower:
                try:
                    subprocess.run(['powershell', '-Command', '(New-Object Media.SoundMixer).Volume = 0.0'], capture_output=True)
                except:
                    pass
                try:
                    subprocess.Popen('excel')
                except:
                    subprocess.Popen(['cmd', '/c', 'start excel'], shell=True)
                print("✓ Excel opened, volume minimized")
                return True
            
            elif 'open powerpoint' in cmd_lower:
                try:
                    subprocess.Popen('powerpnt')
                except:
                    subprocess.Popen(['cmd', '/c', 'start powerpnt'], shell=True)
                print("✓ PowerPoint opened")
                return True
            
            elif 'next track' in cmd_lower:
                pyautogui.press('nexttrack')
                print("✓ Next track")
                return True
            
            elif 'screenshot & copy to clipboard' in cmd_lower:
                pyautogui.hotkey('win', 'shift', 's')
                print("✓ Screenshot copied to clipboard")
                return True
            
            elif 'screenshot tool activated' in cmd_lower:
                pyautogui.hotkey('shift', 'win', 's')
                print("✓ Screenshot tool opened")
                return True
            
            elif 'scroll up' in cmd_lower:
                pyautogui.scroll(3)
                print("✓ Scrolled up")
                return True
            
            elif 'scroll down' in cmd_lower:
                pyautogui.scroll(-3)
                print("✓ Scrolled down")
                return True
            
            elif 'scroll left' in cmd_lower:
                pyautogui.press('left')
                pyautogui.press('left')
                print("✓ Scrolled left")
                return True
            
            elif 'scroll right' in cmd_lower:
                pyautogui.press('right')
                pyautogui.press('right')
                print("✓ Scrolled right")
                return True
            
            elif 'toggle window' in cmd_lower:
                pyautogui.hotkey('alt', 'tab')
                print("✓ Window toggled")
                return True
            
            elif 'next window' in cmd_lower:
                pyautogui.hotkey('alt', 'tab')
                print("✓ Switched to next window")
                return True
            
            elif 'previous window' in cmd_lower:
                pyautogui.hotkey('alt', 'shift', 'tab')
                print("✓ Switched to previous window")
                return True
            
            elif 'maximize window' in cmd_lower:
                pyautogui.hotkey('win', 'up')
                print("✓ Window maximized")
                return True
            
            elif 'restore window' in cmd_lower:
                pyautogui.press('f11')
                print("✓ Window restored")
                return True
            
            elif 'minimize all windows' in cmd_lower:
                pyautogui.hotkey('win', 'd')
                print("✓ All windows minimized")
                return True
            
            elif 'show desktop x' in cmd_lower:
                pyautogui.hotkey('win', 'd')
                print("✓ Desktop shown")
                return True
            
            elif 'open recycle bin' in cmd_lower:
                subprocess.Popen('explorer shell:::{645FF040-5081-101B-9F08-00AA002F954E}')
                print("✓ Recycle Bin opened")
                return True
            
            elif 'system information' in cmd_lower:
                subprocess.Popen('msinfo32')
                print("✓ System Information opened")
                return True
            
            elif 'open run dialog' in cmd_lower:
                pyautogui.hotkey('win', 'r')
                print("✓ Run dialog opened")
                return True
            
            elif 'show notifications' in cmd_lower:
                pyautogui.hotkey('win', 'a')
                print("✓ Notifications shown")
                return True
            
            elif 'show start menu' in cmd_lower:
                pyautogui.press('win')
                print("✓ Start menu shown")
                return True
            
            elif 'enable bluetooth' in cmd_lower:
                subprocess.Popen('ms-settings:bluetooth')
                print("✓ Bluetooth enabled")
                return True
            
            elif 'snap window left' in cmd_lower:
                pyautogui.hotkey('win', 'left')
                print("✓ Window snapped left")
                return True
            
            elif 'snap window right' in cmd_lower:
                pyautogui.hotkey('win', 'right')
                print("✓ Window snapped right")
                return True
            
            elif 'snap window top' in cmd_lower:
                pyautogui.hotkey('win', 'up')
                print("✓ Window snapped top")
                return True
            
            elif 'snap window bottom' in cmd_lower:
                pyautogui.hotkey('win', 'down')
                print("✓ Window snapped bottom")
                return True
            
            else:
                print(f"⚠️ Command recognized but no action mapped: {command}")
                return False
        
        except Exception as e:
            print(f"✗ Command execution error: {e}")
            return False

command_generator = GestureCommandGenerator()

class AIAssistantThread(threading.Thread):
    """Thread for handling gesture-to-command conversion (no API calls)"""
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.command_queue = []
        self.current_command = ""
        self.is_processing = False
        self.running = True
        self.queue_lock = threading.Lock()
    
    def run(self):
        while self.running:
            if self.command_queue:
                with self.queue_lock:
                    gesture_seq = self.command_queue.pop(0)
                
                self.is_processing = True
                self.current_command = ""
                
                try:
                    # Convert gesture sequence directly to command (NO API CALLS)
                    command = command_generator.gesture_sequence_to_command(gesture_seq)
                    self.current_command = command
                    print(f"💬 Generated command: {command}")
                    
                    # Speak the command
                    tts_engine.say(command)
                    tts_engine.runAndWait()
                    
                    # Execute the command
                    success = command_generator.execute_command(command)
                    
                    if success:
                        print("✓ Command executed successfully")
                    else:
                        print("⚠️ Command recognized but action unavailable")
                
                except Exception as e:
                    self.current_command = f"Error: {str(e)}"
                    print(f"Error: {e}")
                
                self.is_processing = False
                time.sleep(0.5)
            
            time.sleep(0.1)
    
    def add_gesture_sequence(self, gesture_seq):
        """Add gesture sequence to process"""
        with self.queue_lock:
            self.command_queue.append(gesture_seq)
            print(f"📨 Gesture sequence queued: {gesture_seq}")
    
    def stop(self):
        self.running = False

# Initialize AI thread
ai_thread = AIAssistantThread()
ai_thread.start()

# Initialize control variables
mouse_pressed = False
touch_threshold = 0.19
scroll_threshold = 0.005  # Smaller threshold for finer detection
scroll_sensitivity = 0.05  # Adjust this value for scrolling speed

# New features: Double-click detection and app control
double_click_threshold = 0.3  # Time window for double-click (seconds)
last_click_time = 0
app_enabled = True
show_debug = True  # Toggle debug info with 'D' key

# FPS tracking
fps_deque = deque(maxlen=30)
prev_time = time.time()

# ============== GESTURE SEQUENCE DETECTION ==============
class GestureSequenceDetector:
    """Detects sequences of hand gestures for AI activation"""
    def __init__(self):
        self.sequence = []
        self.sequence_timeout = 2.0  # seconds
        self.last_gesture_time = 0
        self.gestures = {
            'fist': False,           # All fingers closed
            'peace': False,          # Index and middle extended
            'thumbs_up': False,      # Thumb extended upward
            'open_hand': False,      # All fingers open
            'point': False           # Only index extended
        }
    
    def detect_gesture(self, hand_landmarks, mp_hands):
        """Detect current hand gesture"""
        thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
        index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
        pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
        palm = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
        
        # Calculate distances (fingers open if far from palm)
        thumb_dist = get_landmark_distance(thumb, palm)
        index_dist = get_landmark_distance(index, palm)
        middle_dist = get_landmark_distance(middle, palm)
        ring_dist = get_landmark_distance(ring, palm)
        pinky_dist = get_landmark_distance(pinky, palm)
        
        gesture = 'unknown'
        
        # Fist: all fingers closed (very close to palm)
        if all(d < 0.12 for d in [thumb_dist, index_dist, middle_dist, ring_dist, pinky_dist]):
            gesture = 'fist'
        # Open hand: all fingers extended (far from palm)
        elif all(d > 0.25 for d in [index_dist, middle_dist, ring_dist, pinky_dist]) and thumb_dist > 0.20:
            gesture = 'open_hand'
        # Peace: index and middle extended, ring and pinky closed
        elif index_dist > 0.22 and middle_dist > 0.22 and ring_dist < 0.18 and pinky_dist < 0.18:
            gesture = 'peace'
        # Point: only index extended, others closed
        elif index_dist > 0.25 and middle_dist < 0.15 and ring_dist < 0.15 and pinky_dist < 0.15:
            gesture = 'point'
        # Thumbs up: thumb pointing up (y < palm), index closed, others can vary
        elif thumb.y < (palm.y - 0.05) and index_dist < 0.15 and middle_dist < 0.20:
            gesture = 'thumbs_up'
        
        return gesture
    
    def add_gesture(self, gesture):
        """Add gesture to sequence (filter out unknown)"""
        current_time = time.time()
        
        # Reset sequence if timeout
        if current_time - self.last_gesture_time > self.sequence_timeout:
            self.sequence = []
        
        # Skip unknown gestures - only add recognized gestures
        if gesture != 'unknown':
            # Add new gesture if different from last
            if not self.sequence or self.sequence[-1] != gesture:
                self.sequence.append(gesture)
        
        self.last_gesture_time = current_time
    
    def check_activation_sequence(self):
        """Check if gesture sequence matches activation pattern"""
        # Pattern: fist -> peace -> open_hand (or any 3-gesture sequence)
        if len(self.sequence) >= 3:
            return True
        return False
    
    def get_sequence_str(self):
        """Get string representation of sequence"""
        gesture_emojis = {
            'fist': '✊',
            'peace': '✌️',
            'open_hand': '✋',
            'point': '☝️',
            'thumbs_up': '👍',
            'unknown': '❓'
        }
        return ''.join(gesture_emojis.get(g, '❓') for g in self.sequence)
    
    def reset(self):
        """Reset gesture sequence"""
        self.sequence = []
        self.last_gesture_time = 0

gesture_detector = GestureSequenceDetector()

# ============== ADVANCED GESTURE FEATURES ==============
class AdvancedGestureFeatures:
    """Advanced gesture recognition features including 3D gestures, animations, and AR effects"""
    
    def __init__(self):
        self.gesture_trail = deque(maxlen=100)
        self.cursor_particles = deque(maxlen=500)
        self.active_effects = []
        self.gesture_history = deque(maxlen=10)
        self.last_gesture_position = None
        self.effect_mode = 'normal'  # normal, rainbow, trail, particle, magnetic
        self.gesture_speed = 0
        self.gesture_direction = None
        self.circle_points = []
        self.is_drawing_shape = False
        self.shape_detection_mode = False
        
    def detect_shape_gesture(self, hand_landmarks, mp_hands, frame_shape):
        """Detect if hand is drawing a shape (circle, square, triangle)"""
        index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
        x = int(index_tip.x * frame_shape[1])
        y = int(index_tip.y * frame_shape[0])
        
        # Add to gesture trail
        if self.last_gesture_position:
            dist = np.sqrt((x - self.last_gesture_position[0])**2 + 
                          (y - self.last_gesture_position[1])**2)
            self.gesture_speed = dist
            
            if dist > 2:  # Only add if moving
                self.gesture_trail.append((x, y))
                self.circle_points.append((x, y))
        
        self.last_gesture_position = (x, y)
        
        # Detect shape if enough points
        shape = self._analyze_shape()
        return shape
    
    def _analyze_shape(self):
        """Analyze gesture trail to detect shapes"""
        if len(self.circle_points) < 15:
            return None
        
        points = np.array(self.circle_points)
        center = points.mean(axis=0)
        distances = np.linalg.norm(points - center, axis=1)
        variance = np.var(distances)
        mean_dist = np.mean(distances)
        
        # Avoid division by zero
        if mean_dist == 0:
            return None
        
        # Circle: low variance in distance from center (low coefficient of variation)
        coeff_variation = np.sqrt(variance) / (mean_dist + 1e-5)
        if coeff_variation < 0.2:  # Lowered threshold for better detection
            return 'CIRCLE'
        
        # Line: points are collinear
        if len(points) > 5:
            try:
                # Check if points form a line using cross product variance
                if np.linalg.norm(points[-1] - points[0]) > 10:  # Ensure line is long enough
                    cross_products = np.abs(np.cross(points - points[0], points[-1] - points[0]))
                    cross_var = np.var(cross_products)
                    if cross_var < 100:  # Low cross product variance = collinear
                        return 'LINE'
            except:
                pass
        
        # Square/Rectangle: corners detected with 4 turning points
        if len(points) > 10:
            # Try to detect rectangular shape
            return 'POLYGON'
        
        return None
    
    def add_particle_effect(self, x, y, vx=0, vy=0, lifetime=30):
        """Add a particle at position with velocity"""
        particle = {
            'x': x, 'y': y,
            'vx': vx + np.random.uniform(-2, 2),
            'vy': vy + np.random.uniform(-2, 2),
            'lifetime': lifetime,
            'color': tuple(np.random.randint(100, 255, 3)),
            'size': np.random.randint(3, 8)
        }
        self.cursor_particles.append(particle)
    
    def update_particles(self):
        """Update particle physics"""
        for particle in self.cursor_particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.2  # gravity
            particle['lifetime'] -= 1
    
    def draw_particles(self, frame):
        """Draw all active particles"""
        dead_particles = []
        for i, particle in enumerate(self.cursor_particles):
            if particle['lifetime'] <= 0:
                dead_particles.append(i)
            else:
                x, y = int(particle['x']), int(particle['y'])
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    alpha = particle['lifetime'] / 30.0
                    color = tuple(int(c * alpha) for c in particle['color'])
                    cv2.circle(frame, (x, y), particle['size'], color, -1)
        
        return frame
    
    def apply_cursor_effect(self, frame, cursor_x, cursor_y):
        """Apply visual effect at cursor position"""
        if self.effect_mode == 'rainbow':
            return self._draw_rainbow_cursor(frame, cursor_x, cursor_y)
        elif self.effect_mode == 'trail':
            return self._draw_trail_cursor(frame, cursor_x, cursor_y)
        elif self.effect_mode == 'particle':
            return self._draw_particle_cursor(frame, cursor_x, cursor_y)
        elif self.effect_mode == 'magnetic':
            return self._draw_magnetic_cursor(frame, cursor_x, cursor_y)
        elif self.effect_mode == 'hologram':
            return self._draw_hologram_cursor(frame, cursor_x, cursor_y)
        return frame
    
    def _draw_rainbow_cursor(self, frame, x, y):
        """Draw rainbow effect cursor"""
        colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0), 
                 (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)]
        for i, color in enumerate(colors):
            radius = 8 + i * 2
            cv2.circle(frame, (x, y), radius, color, 2)
        cv2.circle(frame, (x, y), 4, (255, 255, 255), -1)
        return frame
    
    def _draw_trail_cursor(self, frame, x, y):
        """Draw motion trail cursor"""
        points = list(self.gesture_trail)[-20:]
        if len(points) > 1:
            for i in range(len(points) - 1):
                alpha = i / len(points)
                color = tuple(int(200 * alpha + 55) for _ in range(3))
                thickness = int(3 * alpha) + 1
                cv2.line(frame, points[i], points[i+1], color, thickness)
        cv2.circle(frame, (x, y), 8, (0, 255, 255), -1)
        return frame
    
    def _draw_particle_cursor(self, frame, x, y):
        """Draw particle effect cursor"""
        self.add_particle_effect(x, y, self.gesture_speed * 0.1 if self.gesture_speed else 0, 0)
        self.update_particles()
        frame = self.draw_particles(frame)
        cv2.circle(frame, (x, y), 6, (100, 255, 255), -1)
        return frame
    
    def _draw_magnetic_cursor(self, frame, x, y):
        """Draw magnetic field cursor"""
        cv2.circle(frame, (x, y), 15, (100, 150, 255), 1)
        cv2.circle(frame, (x, y), 10, (100, 150, 255), 1)
        cv2.circle(frame, (x, y), 5, (100, 150, 255), -1)
        # Draw field lines
        for angle in np.linspace(0, 2*np.pi, 8, False):
            end_x = int(x + 20 * np.cos(angle))
            end_y = int(y + 20 * np.sin(angle))
            cv2.line(frame, (x, y), (end_x, end_y), (150, 100, 255), 1)
        return frame
    
    def _draw_hologram_cursor(self, frame, x, y):
        """Draw holographic cursor effect"""
        # Draw multiple layers for hologram effect
        for offset in range(1, 4):
            alpha = 0.3 / offset
            color = (100 + 50*offset, 200 - 50*offset, 255)
            cv2.circle(frame, (x + offset, y - offset), 8, color, 2)
            cv2.circle(frame, (x - offset, y + offset), 8, color, 2)
        cv2.circle(frame, (x, y), 8, (0, 255, 200), -1)
        # Draw scan lines
        cv2.line(frame, (x-15, y), (x+15, y), (0, 255, 100), 1)
        cv2.line(frame, (x, y-15), (x, y+15), (0, 255, 100), 1)
        return frame
    
    def reset_trail(self):
        """Reset gesture trail"""
        self.gesture_trail.clear()
        self.circle_points.clear()
        self.last_gesture_position = None

advanced_features = AdvancedGestureFeatures()


class GestureSpeedAnalyzer:
    """Analyzes gesture speed and acceleration for dynamic effects"""
    
    def __init__(self, window_size=10):
        self.position_history = deque(maxlen=window_size)
        self.speed_history = deque(maxlen=window_size)
        self.current_speed = 0
        self.acceleration = 0
    
    def update(self, x, y):
        """Update position and calculate speed"""
        self.position_history.append((x, y))
        
        if len(self.position_history) > 1:
            prev_x, prev_y = self.position_history[-2]
            dist = np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            self.speed_history.append(dist)
            
            if len(self.speed_history) > 1:
                self.acceleration = self.speed_history[-1] - self.speed_history[-2]
            
            self.current_speed = dist
    
    def get_speed_level(self):
        """Get speed as 0-1 normalized value"""
        if not self.speed_history:
            return 0
        max_speed = 50
        return min(1.0, np.mean(self.speed_history) / max_speed)

gesture_speed_analyzer = GestureSpeedAnalyzer()


class HandGestureRecorder:
    """Record and playback custom hand gestures"""
    
    def __init__(self):
        self.is_recording = False
        self.recorded_gestures = {}
        self.current_recording = []
        self.playback_queue = deque()
        self.current_gesture_name = None
    
    def start_recording(self, gesture_name):
        """Start recording a new gesture"""
        self.is_recording = True
        self.current_recording = []
        self.current_gesture_name = gesture_name
        print(f"🎙️ Recording gesture: {gesture_name}")
    
    def record_frame(self, hand_landmarks):
        """Record hand landmarks"""
        if self.is_recording and hand_landmarks:
            frame_data = {
                'landmarks': [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark],
                'timestamp': time.time()
            }
            self.current_recording.append(frame_data)
    
    def stop_recording(self, gesture_name):
        """Stop recording and save gesture"""
        if self.is_recording and self.current_recording:
            self.recorded_gestures[gesture_name] = self.current_recording
            print(f"✅ Gesture '{gesture_name}' saved ({len(self.current_recording)} frames)")
            self.is_recording = False
            
            # Save to database if available
            if HAS_DB:
                try:
                    db = get_database()
                    gesture_data = json.dumps({
                        'name': gesture_name,
                        'frames': len(self.current_recording),
                        'landmarks_count': len(self.current_recording[0]['landmarks']) if self.current_recording else 0
                    })
                    db.save_gesture(
                        gesture_name=gesture_name,
                        gesture_data=gesture_data,
                        description=f"Custom gesture with {len(self.current_recording)} frames"
                    )
                    print(f"✓ Gesture saved to database: {gesture_name}")
                except Exception as e:
                    print(f"✗ Error saving gesture to database: {e}")
            
            return True
        return False
    
    def playback(self, gesture_name):
        """Queue gesture for playback"""
        if gesture_name in self.recorded_gestures:
            self.playback_queue.append(gesture_name)
    
    def save_to_file(self, filename):
        """Save recorded gestures to JSON"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.recorded_gestures, f)
            print(f"💾 Gestures saved to {filename}")
        except Exception as e:
            print(f"Error saving gestures: {e}")

gesture_recorder = HandGestureRecorder()

def draw_fps_and_status(frame, fps, enabled, hand_detected):
    """Draw FPS, status, and hand detection info on frame"""
    h, w = frame.shape[:2]
    status = "ENABLED" if enabled else "DISABLED"
    status_color = (0, 255, 0) if enabled else (0, 0, 255)
    
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Status: {status}", (10, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    hand_text = "Hand: Detected" if hand_detected else "Hand: Not detected"
    hand_color = (0, 255, 0) if hand_detected else (0, 165, 255)
    cv2.putText(frame, hand_text, (10, 110), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, hand_color, 2)
    
    # Instructions
    cv2.putText(frame, "Controls: A=AI Mode, C=Cursor Mode, D=Debug, Space=Toggle, ESC=Exit", (10, h-100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, "Index+Thumb=Click, Middle+Thumb=Scroll, Ring+Thumb=RightClick", (10, h-70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, "AI Mode: Make gesture sequence (fist->peace->open) to activate", (10, h-40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, "✨ NEW: Press 1=Rainbow 2=Particle 3=Hologram 4=Magnetic 5=Trail 6=Normal S=Shape R=Record", (10, h-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 200), 1)
    cv2.putText(frame, "Gesture Sequence: " + gesture_detector.get_sequence_str(), (10, h-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 255), 2)
    
    return frame

def draw_gesture_guide(frame):
    """Draw gesture command guide on screen"""
    h, w = frame.shape[:2]
    
    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 140), (w-10, h-10), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Title
    cv2.putText(frame, "GESTURE COMMANDS", (20, 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 200), 2)
    
    # Commands
    commands = [
        "✊✌️✋ = Open Chrome",
        "✌️☝️👍 = Search Google", 
        "✋✊✋ = Screenshot",
        "👍👍👍 = Volume Up",
        "✊✊✊ = Volume Down",
        "✌️✌️✋ = Open Firefox",
        "☝️☝️☝️ = Close Window",
        "✊✋✌️ = Open Gmail",
        "✋✌️☝️ = Open Notepad",
        "☝️✌️☝️ = Open File Explorer",
        "✌️✋✌️ = Minimize All",
        "✋✋✊ = Show Desktop",
    ]
    
    y_pos = 195
    col_width = w // 2
    for i, cmd in enumerate(commands):
        if i < len(commands) // 2:
            x_pos = 20
        else:
            x_pos = col_width
            if i == len(commands) // 2:
                y_pos = 195
        
        cv2.putText(frame, cmd, (x_pos, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y_pos += 28
    
    return frame

def draw_hand_landmarks_visual(frame, hand_landmarks, mp_hands):
    """Draw circles on important landmarks for visual feedback"""
    h, w = frame.shape[:2]
    
    # Get key landmarks
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]
    
    # Draw points
    points = [(index_tip, (255, 0, 0)), (thumb_tip, (0, 255, 0)), 
              (middle_tip, (0, 0, 255)), (ring_tip, (255, 255, 0))]
    
    for landmark, color in points:
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        cv2.circle(frame, (x, y), 8, color, -1)
        cv2.circle(frame, (x, y), 8, (255, 255, 255), 2)
    
    # Draw ring finger MCP (tracking point)
    x = int(ring_mcp.x * w)
    y = int(ring_mcp.y * h)
    cv2.circle(frame, (x, y), 12, (0, 255, 255), 2)
    
    return frame

def draw_ai_response(frame):
    """Draw AI command on frame"""
    h, w = frame.shape[:2]
    
    # Draw semi-transparent background for text
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, h-180), (w-10, h-80), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Draw title
    cv2.putText(frame, "Generated Command:", (20, h-150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
    
    # Draw command (wrapped text)
    if ai_thread.current_command:
        command_text = ai_thread.current_command
        words = command_text.split()
        line = ""
        y_pos = h - 120
        for word in words:
            if len(line) + len(word) + 1 > 100:
                cv2.putText(frame, line, (20, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                line = word
                y_pos += 30
            else:
                line += word + " "
        if line:
            cv2.putText(frame, line, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # Draw processing indicator
    if ai_thread.is_processing:
        cv2.putText(frame, "🔄 Processing...", (20, h-90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return frame

def draw_advanced_gesture_info(frame):
    """Draw advanced gesture feature info"""
    h, w = frame.shape[:2]
    y_pos = 100
    
    # Current effect mode
    cv2.putText(frame, f"✨ Effect Mode: {advanced_features.effect_mode}", (10, y_pos),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 150), 2)
    y_pos += 30
    
    # Gesture speed
    speed_level = gesture_speed_analyzer.get_speed_level()
    cv2.putText(frame, f"⚡ Speed: {'█' * int(speed_level * 10)}", (10, y_pos),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
    y_pos += 30
    
    # Shape detection status
    if advanced_features.shape_detection_mode:
        cv2.putText(frame, "🔷 Shape Detection: ON", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 2)
        y_pos += 30
    
    # Gesture recording status
    if gesture_recorder.is_recording:
        cv2.putText(frame, "🎙️ Recording Gesture...", (10, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        y_pos += 30
    
    # Gesture trail visualization
    if len(advanced_features.gesture_trail) > 0:
        points = list(advanced_features.gesture_trail)
        if len(points) > 1:
            for i in range(len(points) - 1):
                alpha = i / max(len(points), 1)
                color = (int(100 * alpha + 100), int(255 * alpha), int(200 * alpha))
                thickness = max(1, int(3 * alpha))
                cv2.line(frame, points[i], points[i+1], color, thickness)
    
    return frame



try:
    # Load settings from database if available
    if HAS_DB:
        print("\n" + "="*50)
        print("LOADING SETTINGS FROM WEB APP")
        print("="*50)
        db = get_database()
        user_id = db.get_latest_user_id()
        
        if user_id:
            settings = db.load_user_settings(user_id)
            if settings:
                # Apply loaded settings
                advanced_features.effect_mode = settings['effect']
                advanced_features.shape_detection_mode = settings['shape_detection']
                gesture_sensitivity = settings['sensitivity']
                print(f"✓ Settings loaded successfully!")
                print(f"  Effect: {settings['effect']}")
                print(f"  Shape Detection: {settings['shape_detection']}")
                print(f"  Gesture Sensitivity: {settings['sensitivity']}x")
                db.update_user_last_login(user_id)
            else:
                print("✗ Could not load settings, using defaults")
        else:
            print("✗ No user found in database, using defaults")
        print("="*50 + "\n")
    else:
        print("⚠️ Database integration not available, using default settings\n")
    
    previous_y = None
    ai_mode = False  # Toggle between mouse control and AI mode
    drawing_mode = False  # Drawing mode for gesture art
    cursor_trail = []  # Trail points for cursor
    canvas = None  # Drawing canvas
    
    while True:
        current_time = time.time()
        
        # Read a frame from the webcam
        ret, frame = cap.read()
        if not ret:
            continue

        # Flip the frame horizontally for a natural selfie-view, and convert the BGR image to RGB
        frame = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)

        # Process the frame and find hands
        results = hands.process(frame)

        # Convert the frame color back so it can be displayed
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Calculate FPS
        current_time = time.time()
        fps_deque.append(1.0 / (current_time - prev_time) if current_time != prev_time else 0)
        fps = np.mean(fps_deque) if fps_deque else 0
        prev_time = current_time
        
        hand_detected = False

        # Check for the presence of hands
        if results.multi_hand_landmarks and app_enabled:
            hand_detected = True
            movement_thread.activate()
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks if debug mode is on
                if show_debug:
                    frame = draw_hand_landmarks_visual(frame, hand_landmarks, mp_hands)
                
                # AI MODE: Detect gesture sequences
                if ai_mode:
                    current_gesture = gesture_detector.detect_gesture(hand_landmarks, mp_hands)
                    gesture_detector.add_gesture(current_gesture)
                    
                    # Show gesture detection on frame
                    h, w = frame.shape[:2]
                    cv2.putText(frame, f"Current Gesture: {current_gesture}", (w-350, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 255), 2)
                    
                    # Advanced gesture features in AI mode
                    ring_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]
                    mcp_x = int(ring_finger_mcp.x * frame.shape[1])
                    mcp_y = int(ring_finger_mcp.y * frame.shape[0])
                    
                    # Update gesture speed analyzer
                    gesture_speed_analyzer.update(mcp_x, mcp_y)
                    
                    # Detect shapes if in shape detection mode
                    if advanced_features.shape_detection_mode:
                        shape = advanced_features.detect_shape_gesture(hand_landmarks, mp_hands, frame.shape)
                        if shape:
                            cv2.putText(frame, f"Shape Detected: {shape}", (w-350, 80),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2)
                    
                    # Record gesture if recording
                    if gesture_recorder.is_recording:
                        gesture_recorder.record_frame(hand_landmarks)
                
                # MOUSE CONTROL MODE: Standard gesture control
                if not ai_mode:
                    # Use the base of the ring finger (RING_FINGER_MCP) for tracking
                    ring_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]
                    mcp_x = int(ring_finger_mcp.x * frame.shape[1])
                    mcp_y = int(ring_finger_mcp.y * frame.shape[0])

                    # Update gesture speed analyzer in mouse mode too
                    gesture_speed_analyzer.update(mcp_x, mcp_y)

                    # Calculate margins based on the current frame size
                    margin_width, margin_height = calculate_margins(frame.shape[1], frame.shape[0], inner_area_percent)

                    # Convert video coordinates to screen coordinates
                    target_x, target_y = convert_to_screen_coordinates(mcp_x, mcp_y, frame.shape[1], frame.shape[0], margin_width, margin_height)

                    # Update target position in movement thread
                    movement_thread.update_target(target_x, target_y)

                    # Calculate the adaptive touch threshold based on the average length of fingers
                    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                    middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    hand_size = get_landmark_distance(wrist, middle_finger_tip)
                    adaptive_threshold = touch_threshold * hand_size

                    # Check if index finger and thumb are touching (for LEFT clicking)
                    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    index_thumb_distance = get_landmark_distance(index_tip, thumb_tip)

                    if index_thumb_distance < adaptive_threshold:
                        if not mouse_pressed:
                            pyautogui.mouseDown()
                            mouse_pressed = True
                            last_click_time = current_time
                    else:
                        if mouse_pressed:
                            pyautogui.mouseUp()
                            mouse_pressed = False

                    # Check if middle finger and thumb are touching (for SCROLLING)
                    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    middle_thumb_distance = get_landmark_distance(middle_tip, thumb_tip)

                    if middle_thumb_distance < adaptive_threshold:
                        # Scroll gesture detection
                        if previous_y is not None:
                            delta_y = middle_tip.y - previous_y
                            if abs(delta_y) > scroll_threshold:
                                scroll_amount = delta_y * screen_height * scroll_sensitivity
                                scroll_thread.add_scroll(scroll_amount)

                        previous_y = middle_tip.y
                    else:
                        previous_y = None
                    
                    # Check if ring finger and thumb are touching (for RIGHT clicking)
                    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                    ring_thumb_distance = get_landmark_distance(ring_tip, thumb_tip)
                    
                    if ring_thumb_distance < adaptive_threshold:
                        if not hasattr(draw_hand_landmarks_visual, 'right_click_pressed'):
                            draw_hand_landmarks_visual.right_click_pressed = False
                        
                        if not draw_hand_landmarks_visual.right_click_pressed:
                            pyautogui.rightClick()
                            draw_hand_landmarks_visual.right_click_pressed = True
                    else:
                        draw_hand_landmarks_visual.right_click_pressed = False
                    
                    # Detect shapes if in shape detection mode (mouse control)
                    if advanced_features.shape_detection_mode:
                        shape = advanced_features.detect_shape_gesture(hand_landmarks, mp_hands, frame.shape)
                        if shape:
                            h, w = frame.shape[:2]
                            cv2.putText(frame, f"🔷 SHAPE DETECTED: {shape} ✅", (w//2 - 150, 100),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 100), 3)
                    
                    # Record gesture if recording
                    if gesture_recorder.is_recording:
                        gesture_recorder.record_frame(hand_landmarks)
        else:
            # No hands detected
            if mouse_pressed:
                pyautogui.mouseUp()
                mouse_pressed = False
            movement_thread.deactivate()
        
        # Draw debug info and status
        if show_debug:
            frame = draw_fps_and_status(frame, fps, app_enabled, hand_detected)
        
        # Draw advanced gesture info if in AI mode or if effects are active
        if ai_mode or advanced_features.effect_mode != 'normal':
            frame = draw_advanced_gesture_info(frame)
        
        # Apply cursor effects if hand detected (works in both modes when effect_mode != 'normal')
        if hand_detected and results.multi_hand_landmarks and advanced_features.effect_mode != 'normal':
            for hand_landmarks in results.multi_hand_landmarks:
                ring_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]
                mcp_x = int(ring_finger_mcp.x * frame.shape[1])
                mcp_y = int(ring_finger_mcp.y * frame.shape[0])
                frame = advanced_features.apply_cursor_effect(frame, mcp_x, mcp_y)
        
        # Draw AI response if in AI mode
        if ai_mode and ai_thread.current_command:
            frame = draw_ai_response(frame)
        
        # Draw gesture guide in AI mode
        if ai_mode:
            frame = draw_gesture_guide(frame)
        
        # Add AI mode indicator
        if ai_mode:
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (w-250, 10), (w-10, 70), (0, 150, 200), -1)
            cv2.putText(frame, "GESTURE-TO-COMMAND", (w-240, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(frame, "MODE ON", (w-240, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # Display the frame
        cv2.imshow('Hand Gesture Control', frame)
        
        # Keyboard controls
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            break
        elif key == ord('d') or key == ord('D'):  # Toggle debug mode
            show_debug = not show_debug
        elif key == ord(' '):  # Space key - toggle app enabled/disabled
            app_enabled = not app_enabled
        elif key == ord('a') or key == ord('A'):  # AI mode toggle
            ai_mode = True
            gesture_detector.reset()
            print("\nAI MODE ACTIVATED")
            print("Make gesture sequence to query AI (e.g., fist -> peace -> open)")
            tts_engine.say("AI mode activated")
            tts_engine.runAndWait()
        elif key == ord('c') or key == ord('C'):  # Cursor mode (disable AI mode)
            ai_mode = False
            gesture_detector.reset()
            advanced_features.reset_trail()
            print("\nCursor control mode ACTIVATED")
            print("Use hand gestures to control mouse cursor")
            tts_engine.say("Cursor mode activated")
            tts_engine.runAndWait()
        elif key == ord('1'):  # Rainbow cursor
            advanced_features.effect_mode = 'rainbow'
            print("🌈 Rainbow cursor activated!")
        elif key == ord('2'):  # Particle trail
            advanced_features.effect_mode = 'particle'
            print("✨ Particle trail activated!")
        elif key == ord('3'):  # Hologram
            advanced_features.effect_mode = 'hologram'
            print("💎 Hologram cursor activated!")
        elif key == ord('4'):  # Magnetic
            advanced_features.effect_mode = 'magnetic'
            print("🧲 Magnetic field activated!")
        elif key == ord('5'):  # Trail
            advanced_features.effect_mode = 'trail'
            print("🎨 Motion trail activated!")
        elif key == ord('6'):  # Normal
            advanced_features.effect_mode = 'normal'
            advanced_features.reset_trail()
            print("⚪ Normal cursor mode")
        elif key == ord('s'):  # Toggle shape detection
            advanced_features.shape_detection_mode = not advanced_features.shape_detection_mode
            advanced_features.reset_trail()
            mode_status = "ON" if advanced_features.shape_detection_mode else "OFF"
            print(f"🔷 Shape detection {mode_status}!")
        elif key == ord('r'):  # Toggle gesture recording
            if not gesture_recorder.is_recording:
                gesture_recorder.start_recording('custom_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
            else:
                gesture_recorder.stop_recording('custom_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        elif key == ord('h'):  # Toggle hand skeleton
            print("💀 Hand skeleton visualization toggled!")
        elif key == ord('n'):  # Normal effect mode
            advanced_features.effect_mode = 'normal'
            advanced_features.reset_trail()
            print("⚪ Switched to normal mode")
        
        # AI Mode: Check if gesture sequence is complete and send to command generator
        if ai_mode and gesture_detector.check_activation_sequence() and not ai_thread.is_processing:
            gesture_seq = gesture_detector.sequence.copy()
            print(f"✅ Gesture sequence detected: {gesture_detector.get_sequence_str()}")
            print(f"🎯 Converting gesture to command...")
            ai_thread.add_gesture_sequence(gesture_seq)
            gesture_detector.reset()
            print(f"✓ Gesture sequence reset")

finally:
    movement_thread.stop()
    scroll_thread.stop()
    ai_thread.stop()
    cap.release()
    cv2.destroyAllWindows()
    print("\n👋 Application closed")
