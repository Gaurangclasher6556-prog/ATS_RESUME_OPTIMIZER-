import sys
import os

# Add the root directory to sys.path so 'backend.server' can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Add the backend directory to sys.path so 'ai_handler' can be imported inside server.py
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.server import app
