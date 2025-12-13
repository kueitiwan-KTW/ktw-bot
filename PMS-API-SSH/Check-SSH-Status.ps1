# Check-SSH-Status.ps1 - Check SSH service status

Write-Host ""
Write-Host "========================================"
Write-Host "  SSH Service Status"
Write-Host "========================================"
Write-Host ""

# Check service
$svc = Get-Service -Name sshd -ErrorAction SilentlyContinue

if ($svc) {
    if ($svc.Status -eq "Running") {
        Write-Host "[ONLINE] SSH Service: Running" -ForegroundColor Green
    } else {
        Write-Host "[OFFLINE] SSH Service: $($svc.Status)" -ForegroundColor Red
    }
    Write-Host "         Startup Type: $($svc.StartType)"
} else {
    Write-Host "[ERROR] SSH Service: Not Installed" -ForegroundColor Red
}

# Check firewall
Write-Host ""
$rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if ($rule) {
    if ($rule.Enabled -eq $true) {
        Write-Host "[OPEN] Firewall Port 22: Allowed" -ForegroundColor Green
    } else {
        Write-Host "[BLOCKED] Firewall Port 22: Disabled" -ForegroundColor Red
    }
} else {
    Write-Host "[BLOCKED] Firewall Port 22: No rule exists" -ForegroundColor Red
}

# Show IP
Write-Host ""
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" }
Write-Host "Server IP Addresses:" -ForegroundColor Cyan
foreach ($ip in $ips) {
    Write-Host "  $($ip.IPAddress)"
}

Write-Host ""
Read-Host "Press Enter to exit"
