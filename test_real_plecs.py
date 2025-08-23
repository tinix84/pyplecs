#!/usr/bin/env python3
"""
Quick test script for real PLECS FastAPI server
"""

import requests
import json

def test_real_plecs_server():
    base_url = "http://127.0.0.1:8005"
    
    print("🔍 Testing Real PLECS Server")
    print("=" * 50)
    
    # Test health check
    print("\n1. Health Check:")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        health_data = response.json()
        print(json.dumps(health_data, indent=2))
        
        if not health_data.get('plecs_initialized', False):
            print("⚠️  PLECS not initialized yet")
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return
    
    # Test simulation to trigger PLECS initialization
    print("\n2. Triggering PLECS Initialization via Simulation:")
    try:
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
        
        print("Sending simulation request...")
        response = requests.post(f"{base_url}/simulate", json=sim_data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Simulation successful!")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Simulation failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Simulation timed out (this might be normal for PLECS initialization)")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
    
    # Test health check again to see if PLECS is now initialized
    print("\n3. Health Check After Simulation:")
    try:
        response = requests.get(f"{base_url}/health")
        health_data = response.json()
        print(json.dumps(health_data, indent=2))
        
        if health_data.get('plecs_initialized', False):
            print("✅ PLECS is now initialized!")
        else:
            print("❌ PLECS initialization failed")
            if health_data.get('initialization_error'):
                print(f"Error: {health_data['initialization_error']}")
                
    except Exception as e:
        print(f"❌ Final health check failed: {e}")

if __name__ == '__main__':
    test_real_plecs_server()
