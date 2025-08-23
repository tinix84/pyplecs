#!/usr/bin/env python3
"""
FastAPI Integration - 3 Pure Unit Tests for Commit Validation
FAST tests that validate API functionality without any PLECS dependency.
"""

import sys
import os

# Add pyplecs to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_1_import_validation():
    """Test 1: Verify FastAPI integration imports correctly."""
    print("Test 1: Import Validation")
    print("-" * 30)
    
    try:
        # Test import without triggering PLECS
        import examples.integrate_with_fastapi as fastapi_module
        
        # Check core components
        assert hasattr(fastapi_module, 'app')
        assert hasattr(fastapi_module, 'SimulationRequest')
        assert hasattr(fastapi_module, 'run_simulation')
        
        print("  ✓ FastAPI module imports successfully")
        print("  ✓ Core components exist")
        
        # Test Pydantic model
        sim_req = fastapi_module.SimulationRequest(
            parameters={"Vin": 400.0, "L": 0.001}
        )
        assert sim_req.parameters["Vin"] == 400.0
        print("  ✓ SimulationRequest model works")
        
        print("✓ Test 1: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Test 1: FAILED - {e}")
        return False


def test_2_api_endpoints():
    """Test 2: Verify core API endpoints respond correctly."""
    print("\nTest 2: API Endpoints")
    print("-" * 30)
    
    try:
        # Force test mode before any imports
        os.environ['PYPLECS_TEST_MODE'] = 'true'
        
        import examples.integrate_with_fastapi as fastapi_module
        from fastapi.testclient import TestClient
        
        client = TestClient(fastapi_module.app)
        
        # Test health
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("  ✓ Health endpoint")
        
        # Test parameters
        response = client.get("/parameters")
        assert response.status_code == 200
        params = response.json()
        assert isinstance(params, list)
        assert len(params) > 0
        print("  ✓ Parameters endpoint")
        
        # Test root
        response = client.get("/")
        assert response.status_code == 200
        info = response.json()
        assert "version" in info
        print("  ✓ Root endpoint")
        
        print("✓ Test 2: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Test 2: FAILED - {e}")
        return False


def test_3_api_structure():
    """Test 3: Verify API accepts requests and returns proper structure."""
    print("\nTest 3: API Structure")
    print("-" * 30)
    
    try:
        # Ensure test mode
        os.environ['PYPLECS_TEST_MODE'] = 'true'
        
        import examples.integrate_with_fastapi as fastapi_module
        from fastapi.testclient import TestClient
        
        client = TestClient(fastapi_module.app)
        
        # Test basic simulation request structure
        sim_data = {
            "parameters": {
                "Vin": 400.0,
                "Vout": 200.0,
                "L": 0.001,
                "C": 0.0001,
                "R": 10.0
            },
            "save_plot": True
        }
        
        response = client.post("/simulate", json=sim_data)
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert result["status"] == "success"
        assert "simulation_id" in result
        assert "results" in result
        print("  ✓ Simulation API accepts requests")
        print("  ✓ Response has correct structure")
        
        # Test enhanced request
        enhanced_data = {
            "parameters": {"Vin": 500.0, "L": 0.002},
            "plot_title": "Test Plot",
            "description": "API test",
            "simulation_time": 1.5
        }
        
        response = client.post("/simulate", json=enhanced_data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        print("  ✓ Enhanced features accepted")
        
        print("✓ Test 3: PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Test 3: FAILED - {e}")
        return False


def run_commit_tests():
    """Run all 3 commit validation tests."""
    print("FastAPI Integration - 3 Unit Tests for Commit Validation")
    print("=" * 55)
    print("FAST tests - NO PLECS startup required")
    
    results = []
    
    # Run the 3 tests
    results.append(test_1_import_validation())
    results.append(test_2_api_endpoints())
    results.append(test_3_api_structure())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 55)
    print(f"COMMIT VALIDATION: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - COMMIT APPROVED!")
        print("✨ FastAPI integration is ready for production.")
    else:
        print("❌ TESTS FAILED - COMMIT BLOCKED")
        print("⚠️  Fix issues before committing.")
    
    print("=" * 55)
    return passed == total


if __name__ == "__main__":
    success = run_commit_tests()
    sys.exit(0 if success else 1)
