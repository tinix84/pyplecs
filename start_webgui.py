#!/usr/bin/env python3
"""
PyPLECS Web GUI Startup Script

This script starts the PyPLECS web interface for simulation monitoring and control.
"""

import sys
import os
from pathlib import Path
import uvicorn

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from pyplecs.webgui import create_web_app
    
    def main():
        """Main entry point for the web GUI."""
        print("=" * 60)
        print("PyPLECS Web GUI")
        print("=" * 60)
        print("Advanced PLECS Simulation Automation Platform")
        print("Web Interface for Monitoring and Control")
        print()
        
        # Create the FastAPI application
        app, templates = create_web_app()
        
        # Default configuration
        host = "127.0.0.1"
        port = 8001
        
        # Check for environment variables
        if "PYPLECS_HOST" in os.environ:
            host = os.environ["PYPLECS_HOST"]
        if "PYPLECS_PORT" in os.environ:
            try:
                port = int(os.environ["PYPLECS_PORT"])
            except ValueError:
                print(f"Warning: Invalid port '{os.environ['PYPLECS_PORT']}', using default {port}")
        
        print(f"Starting web server at: http://{host}:{port}")
        print()
        print("Available pages:")
        print(f"  • Dashboard:    http://{host}:{port}/")
        print(f"  • Simulations:  http://{host}:{port}/simulations")
        print(f"  • Cache:        http://{host}:{port}/cache")
        print(f"  • Settings:     http://{host}:{port}/settings")
        print()
        print("API endpoints:")
        print(f"  • Status:       http://{host}:{port}/api/status")
        print(f"  • Simulations:  http://{host}:{port}/api/simulations")
        print(f"  • Cache Stats:  http://{host}:{port}/api/cache/stats")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        try:
            # Start the server
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
        except KeyboardInterrupt:
            print("\nShutting down PyPLECS Web GUI...")
        except Exception as e:
            print(f"Error starting server: {e}")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except ImportError as e:
    print("Error: Required dependencies not found.")
    print(f"Details: {e}")
    print()
    print("Please install the required packages:")
    print("  pip install fastapi uvicorn[standard] jinja2 python-multipart")
    print()
    print("Or if using the project virtual environment:")
    print("  source .venv/bin/activate  # On Linux/Mac")
    print("  .venv\\Scripts\\activate     # On Windows")
    print("  pip install -r requirements.txt")
    sys.exit(1)
