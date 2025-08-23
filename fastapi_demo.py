#!/usr/bin/env python3
"""
FastAPI PLECS Integration - Complete Demo Script

This script demonstrates all the API endpoints with real examples using the simple_buck.plecs model.
Run this while the FastAPI server is running in another terminal.

Start server first:
  .venv\Scripts\Activate.ps1 && python examples/integrate_with_fastapi.py --test-mode --port 8003

Then run this demo:
  .venv\Scripts\Activate.ps1 && python fastapi_demo.py
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE = "http://127.0.0.1:8003"
OUTPUT_DIR = Path("fastapi_demo_output")
OUTPUT_DIR.mkdir(exist_ok=True)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_response(response, description="Response"):
    """Print formatted response data."""
    try:
        data = response.json()
        print(f"✅ {description} (Status: {response.status_code})")
        print(json.dumps(data, indent=2))
    except:
        print(f"✅ {description} (Status: {response.status_code})")
        print(f"Raw response: {response.text[:200]}...")

def test_health_check():
    """Test the health endpoint."""
    print_section("Health Check")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        print_response(response, "Health Check")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_api_info():
    """Test the root API info endpoint."""
    print_section("API Information")
    
    try:
        response = requests.get(f"{API_BASE}/")
        print_response(response, "API Information")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API info failed: {e}")
        return False

def test_parameters():
    """Test the parameters endpoint."""
    print_section("Available Simulation Parameters")
    
    try:
        response = requests.get(f"{API_BASE}/parameters")
        print_response(response, "Parameters")
        
        if response.status_code == 200:
            params = response.json()
            print(f"\n📋 Found {len(params)} parameters:")
            for param in params:
                print(f"  • {param['name']}: {param['default_value']} {param['unit']}")
                print(f"    {param['description']}")
                if param.get('min_value') is not None:
                    print(f"    Range: {param['min_value']} - {param['max_value']}")
                print()
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Parameters test failed: {e}")
        return False

def test_simulation():
    """Test running a simulation."""
    print_section("Running PLECS Simulation")
    
    # Define simulation parameters for buck converter
    sim_params = {
        "parameters": {
            "Vin": 400.0,    # Input voltage
            "Vout": 200.0,   # Target output voltage  
            "L": 0.001,      # Inductance (1mH)
            "C": 0.0001,     # Capacitance (100µF)
            "R": 10.0        # Load resistance (10Ω)
        },
        "timeout": 30.0,
        "save_plot": True
    }
    
    print("🔧 Simulation Parameters:")
    for param, value in sim_params["parameters"].items():
        print(f"  {param}: {value}")
    
    try:
        print(f"\n🚀 Starting simulation...")
        response = requests.post(f"{API_BASE}/simulate", json=sim_params)
        print_response(response, "Simulation Request")
        
        if response.status_code == 200:
            result = response.json()
            sim_id = result["simulation_id"]
            status = result["status"]
            
            print(f"\n📊 Simulation Results:")
            print(f"  ID: {sim_id}")
            print(f"  Status: {status}")
            print(f"  Message: {result['message']}")
            
            if result.get("results"):
                results = result["results"]
                if "time_points" in results:
                    print(f"  Time Points: {results['time_points']}")
                if "output_signals" in results:
                    print(f"  Output Signals: {results['output_signals']}")
            
            if result.get("plot_url"):
                print(f"  Plot URL: {result['plot_url']}")
            
            return sim_id if status == "success" else None
        
        return None
    except Exception as e:
        print(f"❌ Simulation test failed: {e}")
        return None

def test_simulation_results(sim_id):
    """Test getting detailed simulation results."""
    print_section(f"Detailed Results for Simulation {sim_id}")
    
    try:
        response = requests.get(f"{API_BASE}/results/{sim_id}")
        print_response(response, "Detailed Results")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📈 Analysis:")
            print(f"  Simulation ID: {data['simulation_id']}")
            print(f"  Timestamp: {time.ctime(data['timestamp'])}")
            
            if "metrics" in data:
                metrics = data["metrics"]
                for metric_name, metric_data in metrics.items():
                    print(f"\n  {metric_name.replace('_', ' ').title()}:")
                    if isinstance(metric_data, dict):
                        for key, value in metric_data.items():
                            if isinstance(value, float):
                                print(f"    {key}: {value:.3f}")
                            else:
                                print(f"    {key}: {value}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Results test failed: {e}")
        return False

def test_plot_download(sim_id):
    """Test downloading the simulation plot."""
    print_section(f"Downloading Plot for Simulation {sim_id}")
    
    try:
        response = requests.get(f"{API_BASE}/plot/{sim_id}")
        
        if response.status_code == 200:
            plot_file = OUTPUT_DIR / f"simulation_{sim_id}.png"
            with open(plot_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Plot downloaded successfully")
            print(f"  File: {plot_file}")
            print(f"  Size: {len(response.content)} bytes")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            return True
        else:
            print(f"❌ Plot download failed (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Plot download failed: {e}")
        return False

def run_comprehensive_demo():
    """Run the complete FastAPI demo."""
    print("🚀 FastAPI PLECS Integration - Comprehensive Demo")
    print("=" * 60)
    print(f"API Endpoint: {API_BASE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    
    test_results = []
    
    # Test all endpoints
    test_results.append(test_health_check())
    test_results.append(test_api_info())
    test_results.append(test_parameters())
    
    # Run simulation and get ID
    sim_id = test_simulation()
    if sim_id:
        test_results.append(True)
        
        # Wait a moment for background processing
        print("\n⏳ Waiting for background plot generation...")
        time.sleep(2)
        
        # Test detailed results
        test_results.append(test_simulation_results(sim_id))
        
        # Test plot download
        test_results.append(test_plot_download(sim_id))
    else:
        test_results.extend([False, False, False])
    
    # Summary
    print_section("Demo Summary")
    passed = sum(test_results)
    total = len(test_results)
    
    test_names = [
        "Health Check",
        "API Information", 
        "Parameters List",
        "Simulation Execution",
        "Detailed Results",
        "Plot Download"
    ]
    
    print("📊 Test Results:")
    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {i+1}. {name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API endpoints working perfectly!")
        print(f"🔍 Check {OUTPUT_DIR} for downloaded plots")
    else:
        print("⚠️  Some tests failed - check server logs")
    
    return passed == total

if __name__ == "__main__":
    print(__doc__)
    
    print("\n🔌 Checking if server is running...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            run_comprehensive_demo()
        else:
            print(f"❌ Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server!")
        print("\nTo start the server, run in another terminal:")
        print("  .venv\\Scripts\\Activate.ps1 && python examples/integrate_with_fastapi.py --test-mode --port 8003")
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
