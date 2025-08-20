#!/usr/bin/env python3
"""
Test script for PyPLECS Web GUI

This script tests the basic functionality of the web interface.
"""

import sys
import os
from pathlib import Path
import asyncio
import aiohttp
import json

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_webgui():
    """Test the web GUI endpoints."""
    base_url = "http://localhost:8001"
    
    print("Testing PyPLECS Web GUI endpoints...")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test endpoints
        endpoints = [
            ("/", "Dashboard"),
            ("/simulations", "Simulations Page"),
            ("/cache", "Cache Management"),
            ("/api/status", "API Status"),
            ("/api/cache/stats", "Cache Statistics"),
        ]
        
        for endpoint, description in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    if status == 200:
                        print(f"✅ {description}: OK ({status})")
                        
                        # For API endpoints, show some content
                        if endpoint.startswith("/api/"):
                            try:
                                data = await response.json()
                                print(f"   Response keys: {list(data.keys())}")
                            except:
                                print(f"   Response length: {len(await response.text())} chars")
                    else:
                        print(f"❌ {description}: HTTP {status}")
                        
            except Exception as e:
                print(f"❌ {description}: Error - {e}")
        
        print()
        print("Web GUI Test Summary:")
        print("- Dashboard and pages should be accessible")
        print("- API endpoints should return JSON responses")
        print("- Static files (CSS, JS) should be served")
        print()
        print("If all tests passed, the web GUI is ready!")

if __name__ == "__main__":
    print("PyPLECS Web GUI Test")
    print("Make sure the web server is running on localhost:8001")
    print()
    
    try:
        asyncio.run(test_webgui())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"Test failed: {e}")
        print("\nTip: Start the web server first with:")
        print("  python start_webgui.py")
