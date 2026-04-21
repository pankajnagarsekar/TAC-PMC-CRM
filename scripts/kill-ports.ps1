# scripts/kill-ports.ps1
# Authoritative Port Cleanup script for Windows (TAC-PMC-CRM)
param (
    [int[]]$Ports = @(8000, 3000, 3001, 19000, 19001, 19002)
)

Write-Host "--- TAC-PMC-CRM PORT CLEANUP ---" -ForegroundColor Cyan

foreach ($port in $Ports) {
    Write-Host "Checking port $port..." -NoNewline
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($connection) {
        $processId = $connection.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host " [OCCUPIED by $($process.Name) PID: $processId]" -ForegroundColor Yellow
            Write-Host "Killing process $processId..." -NoNewline
            Stop-Process -Id $processId -Force
            Write-Host " [DONE]" -ForegroundColor Green
        } else {
            Write-Host " [OCCUPIED by Unknown Process PID: $processId]" -ForegroundColor Red
        }
    } else {
        Write-Host " [FREE]" -ForegroundColor Green
    }
}

Write-Host "--- PORT CLEANUP COMPLETE ---" -ForegroundColor Cyan
