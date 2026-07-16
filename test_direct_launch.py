"""
Direct launcher for the gesture app - use this to test if app.py works
"""

import subprocess
import os
import sys

# Test if we can launch app.py directly
app_path = r'C:\Users\tb266\AI_cursor\app.py'
venv_python = r'C:\Users\tb266\AI_cursor\venv\Scripts\python.exe'

print(f"App path exists: {os.path.exists(app_path)}")
print(f"Python path exists: {os.path.exists(venv_python)}")

if os.path.exists(app_path) and os.path.exists(venv_python):
    print(f"\nLaunching gesture app...")
    print(f"Command: {venv_python} {app_path}")
    
    try:
        # Launch in new console window
        subprocess.Popen(
            [venv_python, app_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=r'C:\Users\tb266\AI_cursor'
        )
        print("✓ Gesture app launched successfully!")
    except Exception as e:
        print(f"✗ Error: {e}")
        # Try without console flags
        try:
            subprocess.Popen([venv_python, app_path], cwd=r'C:\Users\tb266\AI_cursor')
            print("✓ Gesture app launched (without new console)")
        except Exception as e2:
            print(f"✗ Failed: {e2}")
else:
    print("✗ App path or Python executable not found!")
