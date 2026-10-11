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

# Ensure the backend directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [ORBITGUARD AI] MISSION CONTROL API SERVER")
    print("=" * 65)
    print("  Local API URL:        http://127.0.0.1:8000")
    print("  Interactive Swagger:  http://127.0.0.1:8000/docs")
    print("  ReDoc Documentation:  http://127.0.0.1:8000/redoc")
    print("=" * 65 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
