#!/usr/bin/env python3
"""
Real-world FastAPI PLECS Integration Demo

This script demonstrates a complete workflow using the FastAPI PLECS server:
1. Start the server in test mode
2. Get available parameters
3. Run simulations with different parameter sets
4. Retrieve detailed results
5. Download generated plots

Works with data/simple_buck.plecs model
"""

import requests
import json
import time
import subprocess
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration
API_BASE_URL = "http://127.0.0.1:8002"
SERVER_STARTUP_TIMEOUT = 10


class PLECSAPIDemo:
    """Demo class for PLECS FastAPI integration."""
    
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
        self.server_process = None
        self.simulation_results = {}
        
    def start_server(self, test_mode=True, timeout=SERVER_STARTUP_TIMEOUT):
        """Start the FastAPI server."""
        print("🚀 Starting PLECS FastAPI Server...")
        
        # Activate venv and start server
        cmd = [
            "powershell", "-Command",
            f".venv\\Scripts\\Activate.ps1; python examples/integrate_with_fastapi.py"
        ]
        
        if test_mode:
            cmd[-1] += " --test-mode"
            print("   📍 Running in TEST MODE (mock PLECS)")
        else:
            print("   📍 Running with real PLECS integration")
            
        cmd[-1] += f" --port {self.base_url.split(':')[-1]}"
        
        try:
            self.server_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            print(f"   ⏳ Waiting for server startup (max {timeout}s)...")
            for i in range(timeout):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        print(f"   ✅ Server started successfully after {i+1}s")
                        return True
                except:
                    time.sleep(1)
                    
            print("   ❌ Server startup timeout")
            return False
            
        except Exception as e:
            print(f"   ❌ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the FastAPI server."""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print("   ✅ Server stopped")
            except:
                self.server_process.kill()
                print("   ⚠️ Server force-killed")
    
    def get_server_status(self):
        """Get server status and information."""
        print("\n📊 Server Status")
        print("-" * 40)
        
        try:
            # Root endpoint
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Status: {data['message']}")
                print(f"📡 Version: {data['version']}")
                print(f"⚙️ PLECS Status: {data['plecs_status']}")
                print(f"🔗 Available Endpoints: {len(data['endpoints'])}")
                
            # Health check
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"💚 Health: {health['status']}")
                print(f"🔧 PLECS Ready: {health['plecs_initialized']}")
                
        except Exception as e:
            print(f"❌ Status check failed: {e}")
    
    def get_parameters(self):
        """Get available simulation parameters."""
        print("\n🔧 Available Simulation Parameters")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.base_url}/parameters")
            if response.status_code == 200:
                parameters = response.json()
                print(f"📋 Found {len(parameters)} parameters:")
                
                for param in parameters:
                    name = param['name']
                    desc = param['description']
                    default = param['default_value']
                    unit = param['unit']
                    min_val = param.get('min_value', 'N/A')
                    max_val = param.get('max_value', 'N/A')
                    
                    print(f"   • {name}: {desc}")
                    print(f"     Default: {default} {unit}")
                    print(f"     Range: {min_val} - {max_val}")
                    print()
                
                return parameters
            else:
                print(f"❌ Failed to get parameters: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Parameters request failed: {e}")
            return []
    
    def run_simulation(self, parameters, description=""):
        """Run a simulation with given parameters."""
        print(f"\n⚡ Running Simulation: {description}")
        print("-" * 40)
        
        payload = {
            "parameters": parameters,
            "timeout": 30.0,
            "save_plot": True
        }
        
        print("📤 Request parameters:")
        for name, value in parameters.items():
            print(f"   {name}: {value}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/simulate", 
                json=payload,
                timeout=35
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                sim_id = result['simulation_id']
                status = result['status']
                message = result['message']
                
                print(f"✅ Simulation completed in {duration:.2f}s")
                print(f"🆔 Simulation ID: {sim_id}")
                print(f"📊 Status: {status}")
                print(f"💬 Message: {message}")
                
                if 'results' in result and result['results']:
                    results = result['results']
                    if 'time_points' in results:
                        print(f"📈 Time points: {results['time_points']}")
                    if 'output_signals' in results:
                        print(f"📡 Output signals: {results['output_signals']}")
                
                if result.get('plot_url'):
                    print(f"📊 Plot available at: {result['plot_url']}")
                
                # Store result for later analysis
                self.simulation_results[sim_id] = {
                    'parameters': parameters,
                    'description': description,
                    'result': result,
                    'duration': duration
                }
                
                return sim_id
            else:
                print(f"❌ Simulation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Simulation request failed: {e}")
            return None
    
    def get_detailed_results(self, simulation_id):
        """Get detailed results for a simulation."""
        print(f"\n📊 Detailed Results for {simulation_id}")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.base_url}/results/{simulation_id}")
            if response.status_code == 200:
                details = response.json()
                
                print(f"🆔 Simulation ID: {details['simulation_id']}")
                print(f"⏰ Timestamp: {time.ctime(details['timestamp'])}")
                print(f"📊 Status: {details['status']}")
                
                print(f"\n🔧 Parameters used:")
                for name, value in details['parameters'].items():
                    print(f"   {name}: {value}")
                
                if 'data_keys' in details:
                    print(f"\n📈 Available data: {details['data_keys']}")
                
                if 'metrics' in details and details['metrics']:
                    print(f"\n📊 Performance Metrics:")
                    metrics = details['metrics']
                    
                    for metric_name, metric_data in metrics.items():
                        if isinstance(metric_data, dict):
                            print(f"   {metric_name}:")
                            for key, value in metric_data.items():
                                if isinstance(value, (int, float)):
                                    print(f"     {key}: {value:.3f}")
                                else:
                                    print(f"     {key}: {value}")
                        else:
                            print(f"   {metric_name}: {metric_data}")
                
                return details
            else:
                print(f"❌ Failed to get results: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Results request failed: {e}")
            return None
    
    def download_plot(self, simulation_id, save_path=None):
        """Download simulation plot."""
        if save_path is None:
            save_path = f"simulation_plot_{simulation_id}.png"
        
        print(f"\n📊 Downloading Plot for {simulation_id}")
        print("-" * 40)
        
        try:
            response = requests.get(f"{self.base_url}/plot/{simulation_id}")
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Plot saved to: {save_path}")
                print(f"📏 File size: {len(response.content)} bytes")
                return save_path
            else:
                print(f"❌ Failed to download plot: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Plot download failed: {e}")
            return None
    
    def run_demo_scenarios(self):
        """Run a series of demo simulation scenarios."""
        print("\n🎭 Running Demo Scenarios")
        print("=" * 50)
        
        # Scenario 1: Default buck converter
        sim1 = self.run_simulation(
            parameters={
                "Vin": 400.0,
                "Vout": 200.0,
                "L": 1e-3,
                "C": 100e-6,
                "R": 10.0
            },
            description="Default 400V→200V Buck Converter"
        )
        
        # Scenario 2: High efficiency low power
        sim2 = self.run_simulation(
            parameters={
                "Vin": 300.0,
                "Vout": 150.0,
                "L": 2e-3,
                "C": 200e-6,
                "R": 50.0
            },
            description="Low Power High Efficiency (6W)"
        )
        
        # Scenario 3: High power application
        sim3 = self.run_simulation(
            parameters={
                "Vin": 500.0,
                "Vout": 250.0,
                "L": 0.5e-3,
                "C": 300e-6,
                "R": 5.0
            },
            description="High Power Application (12.5kW)"
        )
        
        return [sim1, sim2, sim3]
    
    def analyze_all_results(self):
        """Analyze and compare all simulation results."""
        print("\n📊 Comparative Analysis")
        print("=" * 50)
        
        if not self.simulation_results:
            print("❌ No simulation results to analyze")
            return
        
        print(f"📈 Analyzed {len(self.simulation_results)} simulations:")
        print()
        
        for sim_id, data in self.simulation_results.items():
            desc = data['description']
            params = data['parameters']
            duration = data['duration']
            
            vin = params.get('Vin', 0)
            vout = params.get('Vout', 0)
            r_load = params.get('R', 1)
            power = vout**2 / r_load if r_load > 0 else 0
            efficiency = (vout / vin) * 100 if vin > 0 else 0
            
            print(f"🔹 {desc}")
            print(f"   ID: {sim_id}")
            print(f"   Power: {power:.1f} W")
            print(f"   Efficiency: {efficiency:.1f}%")
            print(f"   Duration: {duration:.2f}s")
            print()


def main():
    """Main demo function."""
    print("🚀 PLECS FastAPI Integration - Real World Demo")
    print("=" * 60)
    print("Demonstrates complete workflow with data/simple_buck.plecs")
    print()
    
    demo = PLECSAPIDemo()
    
    try:
        # Start server
        if not demo.start_server(test_mode=True):
            print("❌ Could not start server. Exiting.")
            return
        
        # Get server status
        demo.get_server_status()
        
        # Get available parameters
        parameters = demo.get_parameters()
        if not parameters:
            print("❌ Could not get parameters. Exiting.")
            return
        
        # Run demo scenarios
        simulation_ids = demo.run_demo_scenarios()
        
        # Get detailed results for each simulation
        for sim_id in simulation_ids:
            if sim_id:
                demo.get_detailed_results(sim_id)
                demo.download_plot(sim_id, f"demo_plot_{sim_id}.png")
        
        # Final analysis
        demo.analyze_all_results()
        
        print("\n🎉 Demo completed successfully!")
        print("📊 Check the downloaded plot files for visual results")
        print(f"🌐 Visit {demo.base_url}/docs for interactive API documentation")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
    finally:
        # Always stop the server
        demo.stop_server()


if __name__ == "__main__":
    main()
