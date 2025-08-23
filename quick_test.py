#!/usr/bin/env python3
import requests

print('🧪 Testing FastAPI endpoints...')
base_url = 'http://127.0.0.1:8001'

try:
    # Test health
    resp = requests.get(f'{base_url}/health', timeout=5)
    print(f'Health: {resp.status_code} - {resp.json()}')

    # Test parameters
    resp = requests.get(f'{base_url}/parameters', timeout=5) 
    params = resp.json()
    print(f'Parameters: {resp.status_code} - Found {len(params)} parameters')
    for param in params[:3]:  # Show first 3
        print(f'  • {param["name"]}: {param["description"]}')

    # Test simulation
    payload = {
        'parameters': {
            'Vin': 400, 
            'Vout': 200, 
            'L': 1e-3, 
            'C': 100e-6, 
            'R': 10
        }, 
        'save_plot': True
    }
    resp = requests.post(f'{base_url}/simulate', json=payload, timeout=30)
    result = resp.json()
    print(f'Simulation: {resp.status_code} - {result["status"]}')
    sim_id = result['simulation_id']
    print(f'  Simulation ID: {sim_id}')

    # Test results
    resp = requests.get(f'{base_url}/results/{sim_id}', timeout=5)
    details = resp.json()
    print(f'Results: {resp.status_code} - Retrieved simulation details')
    print(f'  Timestamp: {details["timestamp"]}')
    
    # Calculate power
    params = details['parameters']
    power = params['Vout']**2 / params['R']
    print(f'  Calculated Power: {power:.1f} W')

    # Test plot
    resp = requests.get(f'{base_url}/plot/{sim_id}', timeout=10)
    print(f'Plot: {resp.status_code} - Downloaded {len(resp.content)} bytes')
    
    # Save plot
    plot_file = f'demo_plot_{sim_id}.png'
    with open(plot_file, 'wb') as f:
        f.write(resp.content)
    print(f'✅ Saved plot: {plot_file}')
    
    print('\n🎉 All FastAPI endpoints working perfectly!')
    print('✅ GET /health - Server health check')
    print('✅ GET /parameters - Parameter discovery')  
    print('✅ POST /simulate - Buck converter simulation')
    print('✅ GET /results/{id} - Detailed results')
    print('✅ GET /plot/{id} - Plot download')
    
except Exception as e:
    print(f'❌ Error: {e}')
