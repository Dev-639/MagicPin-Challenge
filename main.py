"""
Main entrypoint to run the Vera Message Engine Server.
"""

import uvicorn

if __name__ == "__main__":
    print("Starting Vera Message Engine Server on http://127.0.0.1:8000 ...")
    uvicorn.run("engine.server:app", host="127.0.0.1", port=8000, log_level="info")
