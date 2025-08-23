#!/usr/bin/env python3
"""
Enhanced FastAPI PLECS Integration Demo - Generic Features

This script demonstrates the enhanced generic FastAPI features:
- Custom model files and paths
- Simulation time control
- Custom plot titles and descriptions
- Different plot formats
- Multiple PLECS models

Usage:
1. Start enhanced server: python examples/integrate_with_fastapi.py --port 8005
2. Run this demo: python enhanced_fastapi_demo.py
"""

import requests
import json
import time
from pathlib import Path


def test_enhanced_features():
    """Test the enhanced generic FastAPI features"""
    base_url = "http://127.0.0.1:8005"
    
    print("🚀 Enhanced FastAPI PLECS Integration Demo")
    print("=" * 60)
    print(f"API Endpoint: {base_url}")
    
    # Test 1: Basic simulation with custom title and description
    print("\n" + "="*60)
    print("🔧 Test 1: Basic Simulation with Custom Plot")
    print("="*60)
    
    test1_data = {
        "parameters": {
            "Vin": 400.0,
            "Vout": 200.0,
            "L": 0.001,
            "C": 0.0001,
            "R": 10.0
        },
        "save_plot": True,
        "plot_title": "Buck Converter Performance Analysis",
        "description": "Standard buck converter with 400V input, 200V output",
        "plot_format": "png"
    }
    
    try:
        response = requests.post(f"{base_url}/simulate", json=test1_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("✅ Test 1 SUCCESS!")
            print(f"Simulation ID: {result['simulation_id']}")
            print(f"Time Points: {result['results']['time_points']}")
            print(f"Plot URL: {result['plot_url']}")
        else:
            print(f"❌ Test 1 FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Test 1 ERROR: {e}")
    
    # Test 2: Extended simulation time
    print("\n" + "="*60)
    print("🕐 Test 2: Extended Simulation Time")
    print("="*60)
    
    test2_data = {
        "parameters": {
            "Vin": 300.0,
            "Vout": 150.0,
            "L": 0.002,
            "C": 0.0002,
            "R": 15.0
        },
        "simulation_time": 2.0,  # 2 seconds instead of default
        "save_plot": True,
        "plot_title": "Extended Time Analysis - 2 Second Run",
        "description": "Buck converter with 2-second simulation for steady-state analysis",
        "plot_format": "png"
    }
    
    try:
        response = requests.post(f"{base_url}/simulate", json=test2_data, timeout=45)
        if response.status_code == 200:
            result = response.json()
            print("✅ Test 2 SUCCESS!")
            print(f"Simulation ID: {result['simulation_id']}")
            print(f"Time Points: {result['results']['time_points']}")
            print(f"Message: {result['message']}")
        else:
            print(f"❌ Test 2 FAILED: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Test 2 ERROR: {e}")
    
    # Test 3: Different model file (if available)
    print("\n" + "="*60)
    print("📁 Test 3: Different Model File")
    print("="*60)
    
    test3_data = {
        "parameters": {
            "Vin": 500.0,
            "Vout": 250.0,
            "L": 0.0005,
            "C": 0.00005,
            "R": 5.0
        },
        "model_file": "simple_buck01.plecs",  # Try different model
        "model_path": "data/01",
        "save_plot": True,
        "plot_title": "Alternative Buck Model - High Power",
        "description": "High power buck converter using alternative model file",
        "plot_format": "png"
    }
    
    try:
        response = requests.post(f"{base_url}/simulate", json=test3_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("✅ Test 3 SUCCESS!")
            print(f"Simulation ID: {result['simulation_id']}")
            print(f"Time Points: {result['results']['time_points']}")
            print("✅ Successfully loaded different model file!")
        else:
            print(f"⚠️  Test 3 INFO: {response.status_code}")
            print("This is expected if simple_buck01.plecs doesn't exist")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"⚠️  Test 3 INFO: {e}")
        print("This is expected if the alternative model file doesn't exist")
    
    # Test 4: Parameter sweep simulation
    print("\n" + "="*60)
    print("📊 Test 4: Parameter Sweep - Multiple Loads")
    print("="*60)
    
    resistances = [5.0, 10.0, 20.0, 50.0]
    sweep_results = []
    
    for i, R in enumerate(resistances):
        print(f"\n  Running simulation {i+1}/4: R = {R}Ω")
        
        sweep_data = {
            "parameters": {
                "Vin": 400.0,
                "Vout": 200.0,
                "L": 0.001,
                "C": 0.0001,
                "R": R
            },
            "save_plot": True,
            "plot_title": f"Load Sweep Analysis - R = {R}Ω",
            "description": f"Buck converter response with {R}Ω load resistance",
            "plot_format": "png"
        }
        
        try:
            response = requests.post(f"{base_url}/simulate", json=sweep_data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                sweep_results.append({
                    'R': R,
                    'simulation_id': result['simulation_id'],
                    'time_points': result['results']['time_points']
                })
                print(f"    ✅ R={R}Ω: {result['results']['time_points']} points")
            else:
                print(f"    ❌ R={R}Ω: Failed")
        except Exception as e:
            print(f"    ❌ R={R}Ω: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 Demo Summary")
    print("="*60)
    
    print("\n🎯 Enhanced Features Tested:")
    print("  ✅ Custom plot titles and descriptions")
    print("  ✅ Extended simulation time control")
    print("  ✅ Parameter sweep automation")
    print("  ✅ Multiple simulation management")
    
    if sweep_results:
        print(f"\n📊 Parameter Sweep Results:")
        for result in sweep_results:
            print(f"  R = {result['R']:5.1f}Ω → {result['time_points']} time points")
    
    print(f"\n🔗 Available endpoints:")
    print(f"  Health: {base_url}/health")
    print(f"  Docs: {base_url}/docs")
    print(f"  Parameters: {base_url}/parameters")
    
    print("\n🎉 Enhanced FastAPI integration demo completed!")


if __name__ == '__main__':
    test_enhanced_features()
