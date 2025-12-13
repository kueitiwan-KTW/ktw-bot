# Fix-SSH-KeyAuth.ps1
# Fix Windows SSH key authentication

Write-Host ""
Write-Host "========================================"
Write-Host "  Fix SSH Key Authentication"
Write-Host "========================================"
Write-Host ""

# 1. Check .ssh directory
$authKeysPath = "C:\Users\Administrator\.ssh\authorized_keys"
$sshDir = "C:\Users\Administrator\.ssh"

Write-Host "[1/5] Check .ssh directory..." -ForegroundColor Yellow
if (!(Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    Write-Host "      Created" -ForegroundColor Green
} else {
    Write-Host "      Exists" -ForegroundColor Green
}

# 2. Check authorized_keys
Write-Host ""
Write-Host "[2/5] Check authorized_keys..." -ForegroundColor Yellow
if (Test-Path $authKeysPath) {
    Write-Host "      File exists" -ForegroundColor Green
    $keyCount = (Get-Content $authKeysPath).Count
    Write-Host "      Keys: $keyCount" -ForegroundColor Gray
} else {
    Write-Host "      File NOT exist!" -ForegroundColor Red
}

# 3. Fix file permissions (CRITICAL!)
Write-Host ""
Write-Host "[3/5] Fix file permissions..." -ForegroundColor Yellow

icacls $authKeysPath /inheritance:r 2>$null | Out-Null
icacls $authKeysPath /grant "SYSTEM:(F)" 2>$null | Out-Null
icacls $authKeysPath /grant "BUILTIN\Administrators:(F)" 2>$null | Out-Null
icacls $authKeysPath /grant "${env:USERNAME}:(R)" 2>$null | Out-Null

Write-Host "      Permissions fixed" -ForegroundColor Green

# 4. Check sshd_config
Write-Host ""
Write-Host "[4/5] Check sshd_config..." -ForegroundColor Yellow

$sshdConfigPath = "C:\Program Files\OpenSSH-Win64\sshd_config"
if (!(Test-Path $sshdConfigPath)) {
    $sshdConfigPath = "C:\ProgramData\ssh\sshd_config"
}

if (Test-Path $sshdConfigPath) {
    $config = Get-Content $sshdConfigPath -Raw
    
    # Enable pubkey auth
    if ($config -notmatch "PubkeyAuthentication\s+yes") {
        Add-Content -Path $sshdConfigPath -Value "PubkeyAuthentication yes"
        Write-Host "      Enabled PubkeyAuthentication" -ForegroundColor Green
    } else {
        Write-Host "      PubkeyAuthentication already enabled" -ForegroundColor Green
    }
    
    # Comment out admin special rules
    $lines = Get-Content $sshdConfigPath
    $newLines = @()
    foreach ($line in $lines) {
        if ($line -match "^Match Group administrators" -or $line -match "^\s+AuthorizedKeysFile.*PROGRAMDATA") {
            $newLines += "# $line"
        } else {
            $newLines += $line
        }
    }
    $newLines | Set-Content $sshdConfigPath
    
    Write-Host "      Config updated" -ForegroundColor Green
} else {
    Write-Host "      sshd_config not found" -ForegroundColor Red
}

# 5. Restart SSH service
Write-Host ""
Write-Host "[5/5] Restart SSH service..." -ForegroundColor Yellow
Restart-Service sshd
Write-Host "      Service restarted" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================"
Write-Host "  Fix Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Test SSH connection from Mac now" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
