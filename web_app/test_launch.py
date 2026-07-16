"""
Test script to verify gesture app launcher works
"""

import os
import sys
import subprocess

# Simulate what the endpoint does
web_app_dir = r'C:\Users\tb266\AI_cursor\web_app'
os.chdir(web_app_dir)

# Get parent directory (should be AI_cursor)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"Parent dir: {parent_dir}")

# Get app.py path
app_path = os.path.join(parent_dir, 'app.py')
print(f"App path: {app_path}")
print(f"App exists: {os.path.exists(app_path)}")

# Get Python path
print(f"Current Python: {sys.executable}")

# Try to get venv python
venv_python = os.path.join(parent_dir, 'venv', 'Scripts', 'python.exe')
print(f"Venv Python: {venv_python}")
print(f"Venv Python exists: {os.path.exists(venv_python)}")

# Show what will be used
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    python_path = sys.executable
    print(f"Using current Python: {python_path}")
else:
    python_path = venv_python if os.path.exists(venv_python) else 'python'
    print(f"Using fallback Python: {python_path}")

print(f"\nCommand that will be executed:")
print(f"{python_path} {app_path}")
print(f"\nReady to launch!")
