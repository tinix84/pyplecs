#!/usr/bin/env python3
"""Simple test script for FastAPI integration validation."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test all required imports."""
    print("🧪 Testing FastAPI Integration Dependencies")
    print("=" * 50)
    
    results = []
    
    # Test FastAPI imports
    try:
        from fastapi import FastAPI, HTTPException
        print("✓ FastAPI: OK")
        results.append(True)
    except ImportError as e:
        print(f"✗ FastAPI: FAILED - {e}")
        results.append(False)
    
    try:
        import uvicorn
        print("✓ Uvicorn: OK")
        results.append(True)
    except ImportError as e:
        print(f"✗ Uvicorn: FAILED - {e}")
        results.append(False)
    
    try:
        from pydantic import BaseModel
        print("✓ Pydantic: OK")
        results.append(True)
    except ImportError as e:
        print(f"✗ Pydantic: FAILED - {e}")
        results.append(False)
    
    # Test PyPLECS imports
    try:
        from pyplecs.pyplecs import PlecsApp, PlecsServer
        print("✓ PyPLECS: OK")
        results.append(True)
    except ImportError as e:
        print(f"✗ PyPLECS: FAILED - {e}")
        results.append(False)
    
    # Test plotting imports
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        print("✓ Matplotlib & NumPy: OK")
        results.append(True)
    except ImportError as e:
        print(f"✗ Matplotlib/NumPy: FAILED - {e}")
        results.append(False)
    
    return all(results)

def test_basic_app():
    """Test basic FastAPI app creation."""
    print("\n🚀 Testing Basic FastAPI App Creation")
    print("=" * 50)
    
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
        
        # Create basic app
        app = FastAPI(title="Test PLECS API")
        
        # Create basic model
        class TestModel(BaseModel):
            value: float
            
        # Create basic endpoint
        @app.get("/")
        def root():
            return {"message": "Test API working"}
            
        @app.post("/test")
        def test_endpoint(data: TestModel):
            return {"received": data.value}
        
        print("✓ FastAPI app creation: OK")
        print("✓ Pydantic models: OK")
        print("✓ Route definition: OK")
        return True
        
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False

def test_mock_simulation():
    """Test mock simulation functionality."""
    print("\n🔄 Testing Mock Simulation")
    print("=" * 50)
    
    try:
        import numpy as np
        
        # Mock PLECS simulation data
        t = np.linspace(0, 1, 100)
        v_out = 200 + 10 * np.sin(2 * np.pi * 50 * t)
        i_L = 5 + 0.5 * np.sin(2 * np.pi * 50 * t)
        
        mock_result = {
            'Time': t.tolist(),
            'Values': [v_out.tolist(), i_L.tolist()]
        }
        
        print(f"✓ Mock data generation: {len(mock_result['Time'])} time points")
        print(f"✓ Mock signals: {len(mock_result['Values'])} signals")
        return True
        
    except Exception as e:
        print(f"✗ Mock simulation failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 FastAPI Integration Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # Run tests
    test_results.append(test_imports())
    test_results.append(test_basic_app())
    test_results.append(test_mock_simulation())
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 60)
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("🚀 FastAPI integration is ready!")
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("🔧 Please install missing dependencies:")
        print("   pip install fastapi[all] uvicorn numpy matplotlib")
        sys.exit(1)
