import os
import sys

# Wrapper for streamlit_app.py
with open(os.path.join(os.path.dirname(__file__), "streamlit_app.py"), "r", encoding="utf-8") as f:
    code = f.read()

exec(code)
