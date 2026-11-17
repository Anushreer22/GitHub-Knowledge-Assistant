"""Backend Server Launcher for GitHub Knowledge Assistant.
Configures Uvicorn reload directories to strictly watch 'backend/' and ignore 'data/', 'logs/', and repository files,
preventing spurious WatchFiles server restarts during Git clone and indexing.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting GitHub Knowledge Assistant API on http://{host}:{port}")
    print("Reload watching restricted to 'backend/' directory (data/ and logs/ excluded).")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["backend"],
        reload_includes=["*.py"],
        reload_excludes=["data/*", "logs/*", "*.jsonl", "*.pkl", "*.npy", "*.pt", "*.tmp*"]
    )
