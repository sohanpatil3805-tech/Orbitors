import os
import sys

# Force UTF-8 encoding for standard output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn

# Ensure the backend directory is in Python path (app/__init__.py adds the project root for the engine)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

HOST = os.environ.get("ORBITGUARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("ORBITGUARD_PORT", "8000"))

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [ORBITGUARD AI] MISSION CONTROL API SERVER")
    print("=" * 65)
    print(f"  Local API URL:        http://{HOST}:{PORT}")
    print(f"  Interactive Swagger:  http://{HOST}:{PORT}/docs")
    print(f"  ReDoc Documentation:  http://{HOST}:{PORT}/redoc")
    print("  Frontend (Vite) proxies /api here: cd frontend && npm run dev")
    print("  Live screening starts in the background (about a minute on first run)")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True, reload_dirs=[current_dir], app_dir=current_dir)
