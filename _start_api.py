"""Start pyplecs REST API server (for WSL→Windows testing)."""
import sys
from pathlib import Path

# Ensure pyplecs is importable
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

from pyplecs.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
