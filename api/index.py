import os
import sys

# Ensure root directory is on sys.path for Vercel Serverless Function execution
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.server import app

# Export ASGI app for Vercel
__all__ = ["app"]
