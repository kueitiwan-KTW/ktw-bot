# Enable-SSH.ps1 - Windows Server 2016 OpenSSH Setup
# Run as Administrator

Write-Host ""
Write-Host "========================================"
Write-Host "  Enable OpenSSH Server"
Write-Host "========================================"
Write-Host ""

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "[ERROR] Please run as Administrator!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Running as Administrator" -ForegroundColor Green

# Check if sshd service exists
$sshService = Get-Service -Name sshd -ErrorAction SilentlyContinue

if ($sshService) {
    Write-Host "[OK] OpenSSH Server already installed" -ForegroundColor Green
} else {
    Write-Host "[INFO] Installing OpenSSH Server..." -ForegroundColor Yellow
    
    # Try Windows capability first
    try {
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction Stop
        Write-Host "[OK] OpenSSH installed via Windows feature" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Windows feature install failed, trying GitHub download..." -ForegroundColor Yellow
        
        $url = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.5.0.0p1-Beta/OpenSSH-Win64.zip"
        $zipPath = "$env:TEMP\OpenSSH-Win64.zip"
        $installDir = "C:\Program Files\OpenSSH-Win64"
        
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
            
            if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force }
            Expand-Archive -Path $zipPath -DestinationPath "C:\Program Files" -Force
            
            Push-Location $installDir
            powershell.exe -ExecutionPolicy Bypass -File .\install-sshd.ps1
            Pop-Location
            
            Write-Host "[OK] OpenSSH installed from GitHub" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Install failed: $($_.Exception.Message)" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
}

# Start service
Write-Host ""
Write-Host "[INFO] Starting SSH service..." -ForegroundColor Yellow

try {
    Set-Service -Name sshd -StartupType Automatic -ErrorAction Stop
    Start-Service sshd -ErrorAction Stop
    Write-Host "[OK] SSH service started" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Service start failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Firewall
Write-Host ""
Write-Host "[INFO] Configuring firewall..." -ForegroundColor Yellow

$rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if ($rule) {
    Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP"
    Write-Host "[OK] Firewall rule enabled" -ForegroundColor Green
} else {
    try {
        New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH SSH Server" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        Write-Host "[OK] Firewall rule created" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Firewall config failed, please open port 22 manually" -ForegroundColor Yellow
    }
}

# Show result
Write-Host ""
Write-Host "========================================"
Write-Host "  SSH Setup Complete!"
Write-Host "========================================"
Write-Host ""

# Get IP
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" }
Write-Host "Connection Info:" -ForegroundColor Cyan
Write-Host "  Port: 22"
foreach ($ip in $ips) {
    Write-Host "  IP: $($ip.IPAddress)"
}
Write-Host ""
Write-Host "Connect from Mac:"
Write-Host "  ssh username@$($ips[0].IPAddress)" -ForegroundColor Yellow
Write-Host ""

# Check status
$svc = Get-Service sshd -ErrorAction SilentlyContinue
if ($svc.Status -eq "Running") {
    Write-Host "[ONLINE] SSH service is running" -ForegroundColor Green
} else {
    Write-Host "[OFFLINE] SSH service is NOT running" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
