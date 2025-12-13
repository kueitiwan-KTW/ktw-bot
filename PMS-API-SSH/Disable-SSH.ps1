# Disable-SSH.ps1 - Stop OpenSSH Server
# Run as Administrator

Write-Host ""
Write-Host "========================================"
Write-Host "  Disable OpenSSH Server"
Write-Host "========================================"
Write-Host ""

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "[ERROR] Please run as Administrator!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Stop service
Write-Host "[INFO] Stopping SSH service..." -ForegroundColor Yellow

$svc = Get-Service -Name sshd -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -eq "Running") {
        Stop-Service sshd -Force
        Write-Host "[OK] SSH service stopped" -ForegroundColor Green
    } else {
        Write-Host "[INFO] SSH service was not running" -ForegroundColor Cyan
    }
    Set-Service -Name sshd -StartupType Manual
    Write-Host "[OK] Set to Manual startup" -ForegroundColor Green
} else {
    Write-Host "[INFO] SSH service not installed" -ForegroundColor Cyan
}

# Disable firewall rule
Write-Host ""
Write-Host "[INFO] Disabling firewall rule..." -ForegroundColor Yellow

$rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if ($rule) {
    Disable-NetFirewallRule -Name "OpenSSH-Server-In-TCP"
    Write-Host "[OK] Firewall rule disabled (Port 22 blocked)" -ForegroundColor Green
} else {
    Write-Host "[INFO] No firewall rule found" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================"
Write-Host "  SSH Disabled!"
Write-Host "========================================"
Write-Host ""
Write-Host "[LOCKED] Remote SSH connections are now blocked" -ForegroundColor Cyan
Write-Host ""
Write-Host "To re-enable, run Enable-SSH.ps1" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit"
