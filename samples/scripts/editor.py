#!/usr/bin/env python3
"""
EXIF Sample Data Editor launcher

This script sets up the Python path and launches the editor app.
"""

import sys
import os

# Add the editor directory to Python path so imports work cleanly
editor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor")
sys.path.insert(0, editor_dir)

# Now we can import and run the app
from app import EditorApp

if __name__ == "__main__":
    app = EditorApp()
    app.run()