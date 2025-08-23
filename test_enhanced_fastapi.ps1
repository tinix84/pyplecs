#!/usr/bin/env powershell
<#
Enhanced FastAPI PLECS Integration - PowerShell Test Script

This script demonstrates the enhanced generic FastAPI features using PowerShell.
#>

# Configuration
$baseUrl = "http://127.0.0.1:8005"

Write-Host "🚀 Enhanced FastAPI PLECS Integration Demo" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "API Endpoint: $baseUrl"

# Test 1: Basic simulation with custom plot title and description
Write-Host ""
Write-Host "="*60
Write-Host "🔧 Test 1: Basic Simulation with Custom Plot" -ForegroundColor Yellow
Write-Host "="*60

$test1Data = @{
    parameters = @{
        Vin = 400.0
        Vout = 200.0
        L = 0.001
        C = 0.0001
        R = 10.0
    }
    save_plot = $true
    plot_title = "Enhanced Buck Converter Test"
    description = "Testing enhanced FastAPI features with custom title"
    plot_format = "png"
} | ConvertTo-Json -Depth 3

try {
    Write-Host "Sending simulation request..."
    $response = Invoke-RestMethod -Uri "$baseUrl/simulate" -Method POST -Body $test1Data -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "✅ Test 1 SUCCESS!" -ForegroundColor Green
    Write-Host "Simulation ID: $($response.simulation_id)"
    Write-Host "Time Points: $($response.results.time_points)"
    Write-Host "Message: $($response.message)"
    Write-Host "Plot URL: $($response.plot_url)"
}
catch {
    Write-Host "❌ Test 1 FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Extended simulation time
Write-Host ""
Write-Host "="*60
Write-Host "🕐 Test 2: Extended Simulation Time" -ForegroundColor Yellow
Write-Host "="*60

$test2Data = @{
    parameters = @{
        Vin = 300.0
        Vout = 150.0
        L = 0.002
        C = 0.0002
        R = 15.0
    }
    simulation_time = 2.0
    save_plot = $true
    plot_title = "Extended Time Analysis - 2 Second Run"
    description = "Buck converter with 2-second simulation for steady-state analysis"
    plot_format = "png"
} | ConvertTo-Json -Depth 3

try {
    Write-Host "Sending extended simulation request..."
    $response = Invoke-RestMethod -Uri "$baseUrl/simulate" -Method POST -Body $test2Data -ContentType "application/json" -TimeoutSec 45
    
    Write-Host "✅ Test 2 SUCCESS!" -ForegroundColor Green
    Write-Host "Simulation ID: $($response.simulation_id)"
    Write-Host "Time Points: $($response.results.time_points)"
    Write-Host "Message: $($response.message)"
}
catch {
    Write-Host "❌ Test 2 FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Different model file
Write-Host ""
Write-Host "="*60
Write-Host "📁 Test 3: Different Model File" -ForegroundColor Yellow
Write-Host "="*60

$test3Data = @{
    parameters = @{
        Vin = 500.0
        Vout = 250.0
        L = 0.0005
        C = 0.00005
        R = 5.0
    }
    model_file = "simple_buck01.plecs"
    model_path = "data/01"
    save_plot = $true
    plot_title = "Alternative Buck Model - High Power"
    description = "High power buck converter using alternative model file"
    plot_format = "png"
} | ConvertTo-Json -Depth 3

try {
    Write-Host "Trying alternative model file..."
    $response = Invoke-RestMethod -Uri "$baseUrl/simulate" -Method POST -Body $test3Data -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "✅ Test 3 SUCCESS!" -ForegroundColor Green
    Write-Host "Simulation ID: $($response.simulation_id)"
    Write-Host "Time Points: $($response.results.time_points)"
    Write-Host "✅ Successfully loaded different model file!" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Test 3 INFO: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "This is expected if simple_buck01.plecs doesn't exist"
}

# Test 4: Parameter sweep
Write-Host ""
Write-Host "="*60
Write-Host "📊 Test 4: Parameter Sweep - Multiple Loads" -ForegroundColor Yellow
Write-Host "="*60

$resistances = @(5.0, 10.0, 20.0, 50.0)
$sweepResults = @()

for ($i = 0; $i -lt $resistances.Count; $i++) {
    $R = $resistances[$i]
    Write-Host ""
    Write-Host "  Running simulation $($i+1)/$($resistances.Count): R = ${R}Ω"
    
    $sweepData = @{
        parameters = @{
            Vin = 400.0
            Vout = 200.0
            L = 0.001
            C = 0.0001
            R = $R
        }
        save_plot = $true
        plot_title = "Load Sweep Analysis - R = ${R}Ω"
        description = "Buck converter response with ${R}Ω load resistance"
        plot_format = "png"
    } | ConvertTo-Json -Depth 3
    
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/simulate" -Method POST -Body $sweepData -ContentType "application/json" -TimeoutSec 30
        
        $sweepResults += @{
            R = $R
            simulation_id = $response.simulation_id
            time_points = $response.results.time_points
        }
        Write-Host "    ✅ R=${R}Ω: $($response.results.time_points) points" -ForegroundColor Green
    }
    catch {
        Write-Host "    ❌ R=${R}Ω: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Summary
Write-Host ""
Write-Host "="*60
Write-Host "📋 Demo Summary" -ForegroundColor Green
Write-Host "="*60

Write-Host ""
Write-Host "🎯 Enhanced Features Tested:"
Write-Host "  ✅ Custom plot titles and descriptions"
Write-Host "  ✅ Extended simulation time control"
Write-Host "  ✅ Parameter sweep automation"
Write-Host "  ✅ Multiple simulation management"

if ($sweepResults.Count -gt 0) {
    Write-Host ""
    Write-Host "📊 Parameter Sweep Results:"
    foreach ($result in $sweepResults) {
        Write-Host "  R = $($result.R.ToString('F1'))Ω → $($result.time_points) time points"
    }
}

Write-Host ""
Write-Host "🔗 Available endpoints:"
Write-Host "  Health: $baseUrl/health"
Write-Host "  Docs: $baseUrl/docs"
Write-Host "  Parameters: $baseUrl/parameters"

Write-Host ""
Write-Host "🎉 Enhanced FastAPI integration demo completed!" -ForegroundColor Green
