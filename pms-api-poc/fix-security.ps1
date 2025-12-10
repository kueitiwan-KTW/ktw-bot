# Windows Server 安全設定自動修復腳本
# 請以系統管理員身分執行

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "PMS API - Windows 安全設定修復工具"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 檢查是否以系統管理員身分執行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 錯誤：此腳本必須以系統管理員身分執行" -ForegroundColor Red
    Write-Host ""
    Write-Host "請執行以下步驟：" -ForegroundColor Yellow
    Write-Host "1. 右鍵點擊 PowerShell"
    Write-Host "2. 選擇「以系統管理員身分執行」"
    Write-Host "3. 重新執行此腳本"
    Write-Host ""
    pause
    exit 1
}

# 1. 設定執行政策
Write-Host "[1/5] 設定 PowerShell 執行政策..." -ForegroundColor Cyan
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    Write-Host "✅ 完成" -ForegroundColor Green
} catch {
    Write-Host "⚠️  警告：$($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# 2. 加入 Defender 排除
Write-Host "[2/5] 加入 Windows Defender 排除清單..." -ForegroundColor Cyan
try {
    Add-MpPreference -ExclusionPath "C:\KTW-bot" -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionPath "C:\Program Files\nodejs" -ErrorAction SilentlyContinue
    Write-Host "✅ 完成" -ForegroundColor Green
    
    # 顯示排除清單
    $exclusions = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
    if ($exclusions -contains "C:\KTW-bot") {
        Write-Host "   ✓ C:\KTW-bot 已加入排除清單" -ForegroundColor Gray
    }
    if ($exclusions -contains "C:\Program Files\nodejs") {
        Write-Host "   ✓ C:\Program Files\nodejs 已加入排除清單" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  警告：$($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# 3. 解除檔案封鎖
Write-Host "[3/5] 解除檔案封鎖..." -ForegroundColor Cyan
if (Test-Path "C:\KTW-bot\pms-api-poc") {
    try {
        $files = Get-ChildItem "C:\KTW-bot\pms-api-poc" -Recurse -File
        $files | Unblock-File -ErrorAction SilentlyContinue
        Write-Host "✅ 完成 (處理了 $($files.Count) 個檔案)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  警告：$($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  找不到專案目錄：C:\KTW-bot\pms-api-poc" -ForegroundColor Yellow
    Write-Host "   請先部署專案後再執行此腳本" -ForegroundColor Gray
}
Write-Host ""

# 4. 設定防火牆規則
Write-Host "[4/5] 設定防火牆規則..." -ForegroundColor Cyan
try {
    # 檢查規則是否已存在
    $existingRule = Get-NetFirewallRule -DisplayName "PMS API Port 3000" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "   ℹ️  防火牆規則已存在" -ForegroundColor Gray
    } else {
        New-NetFirewallRule -DisplayName "PMS API Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow | Out-Null
        Write-Host "✅ 完成 (已開放 Port 3000)" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  警告：$($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# 5. 檢查 Oracle 服務
Write-Host "[5/5] 檢查 Oracle 服務..." -ForegroundColor Cyan
$oracleServices = Get-Service | Where-Object {$_.Name -like "*Oracle*"}
if ($oracleServices) {
    Write-Host ""
    $oracleServices | Format-Table Name, Status, DisplayName -AutoSize
    
    # 檢查是否有未運行的關鍵服務
    $stoppedServices = $oracleServices | Where-Object {$_.Status -ne "Running"}
    if ($stoppedServices) {
        Write-Host "⚠️  以下 Oracle 服務未運行：" -ForegroundColor Yellow
        $stoppedServices | ForEach-Object {
            Write-Host "   - $($_.DisplayName)" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "   建議執行：" -ForegroundColor Cyan
        Write-Host "   net start OracleServiceGDWUUKT" -ForegroundColor Gray
        Write-Host "   net start OracleOraDB12Home1TNSListener" -ForegroundColor Gray
    } else {
        Write-Host "✅ 所有 Oracle 服務正在運行" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  找不到 Oracle 服務" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ 安全設定完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📝 下一步：" -ForegroundColor Cyan
Write-Host "   1. 繼續執行 install-windows.bat" -ForegroundColor Gray
Write-Host "   2. 或參考 DEPLOY_WINDOWS.md 手動部署" -ForegroundColor Gray
Write-Host ""
pause
