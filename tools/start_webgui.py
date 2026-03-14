#!/usr/bin/env python3
"""
Project-local helper to start the PyPLECS web GUI. Moved from repository root to
`tools/` to keep the repository root minimal.
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn

    from pyplecs.webgui import create_web_app
except Exception as e:
    print('Error importing webgui or uvicorn:', e)
    print('Make sure you created and activated a virtual environment and installed requirements.')
    raise


def main():
    app, templates = create_web_app()
    host = os.environ.get('PYPLECS_HOST', '127.0.0.1')
    port = int(os.environ.get('PYPLECS_PORT', '8001'))
    print(f'Starting PyPLECS Web GUI at http://{host}:{port}')
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
