# Windows Server 安全設定指南

> **重要**：部署前必須先處理 Windows 安全限制

---

## 🛡️ 常見 Windows 安全問題

### 問題 1：檔案被阻擋或刪除

**症狀**：
- 下載的 `.bat` 或 `.js` 檔案消失
- 執行時顯示「Windows 已保護您的電腦」
- npm install 失敗

**原因**：Windows Defender 即時保護

**解決方案**：

```powershell
# 方法 1：加入排除清單（推薦）
# 以系統管理員身分執行

Add-MpPreference -ExclusionPath "C:\KTW-bot"
Add-MpPreference -ExclusionPath "C:\Program Files\nodejs"

# 驗證
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

```powershell
# 方法 2：暫時停用即時保護（不推薦）
Set-MpPreference -DisableRealtimeMonitoring $true
# 部署完成後記得重新啟用
Set-MpPreference -DisableRealtimeMonitoring $false
```

---

### 問題 2：無法執行批次檔或腳本

**症狀**：
- 執行 `install-windows.bat` 無反應
- PowerShell 顯示「禁止執行指令碼」

**原因**：PowerShell 執行政策限制

**解決方案**：

```powershell
# 檢查目前政策
Get-ExecutionPolicy

# 如果是 "Restricted" 或 "AllSigned"，修改為：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或暫時略過限制
powershell -ExecutionPolicy Bypass -File .\install-windows.bat
```

---

### 問題 3：網路連線被阻擋

**症狀**：
- npm install 無法下載套件
- 瀏覽器無法訪問 API (http://localhost:3000)
- LINE BOT 無法連線到 API

**原因**：Windows 防火牆

**解決方案**：

```powershell
# 1. 允許 Node.js 通過防火牆
New-NetFirewallRule -DisplayName "Node.js" -Direction Inbound -Program "C:\Program Files\nodejs\node.exe" -Action Allow

# 2. 開放特定端口（API 端口）
New-NetFirewallRule -DisplayName "PMS API Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# 3. 檢查防火牆規則
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Node*" -or $_.DisplayName -like "*PMS*"}
```

手動設定防火牆：
1. 控制台 → Windows Defender 防火牆
2. 進階設定 → 輸入規則
3. 新增規則 → 端口 → TCP → 特定本機端口：3000
4. 允許連線 → 套用

---

### 問題 4：下載的檔案被標記為「不安全」

**症狀**：
- 檔案圖示上有鎖頭或警告標誌
- 執行時顯示「無法辨識發行者」

**原因**：檔案從網際網路下載標記

**解決方案**：

```powershell
# 批次解除封鎖所有檔案
cd C:\KTW-bot\pms-api-poc
Get-ChildItem -Recurse | Unblock-File
```

手動解除封鎖單一檔案：
1. 右鍵點擊檔案 → 內容
2. 在底部找到「安全性」區段
3. 勾選「解除封鎖」
4. 套用 → 確定

---

### 問題 5：Oracle 資料庫連線失敗

**症狀**：
- `npm test` 顯示 TNS 錯誤
- ORA-12560 或 ORA-12154

**原因**：Oracle 服務未啟動或環境變數錯誤

**解決方案**：

```powershell
# 1. 檢查 Oracle 服務
Get-Service | Where-Object {$_.Name -like "*Oracle*"} | Format-Table Name, Status, DisplayName

# 2. 啟動所有 Oracle 服務
net start OracleServiceGDWUUKT
net start OracleOraDB12Home1TNSListener

# 3. 檢查 TNS 設定
echo %ORACLE_HOME%
dir %ORACLE_HOME%\network\admin\tnsnames.ora
```

設定 Oracle 環境變數（如果需要）：
```powershell
# 設定 ORACLE_HOME
setx ORACLE_HOME "C:\app\oracle\product\12.2.0\dbhome_1" /M

# 加入 PATH
setx PATH "%PATH%;%ORACLE_HOME%\bin" /M
```

---

## 🔐 企業環境特殊限制

### 問題 6：企業防毒軟體

**如果使用 McAfee、Symantec、趨勢科技等企業防毒**：

1. 聯繫 IT 部門
2. 申請加入排除清單：
   - `C:\KTW-bot`
   - `C:\Program Files\nodejs`
3. 或申請臨時停用掃描

### 問題 7：網域政策限制

**如果在 Active Directory 網域環境**：

可能需要 IT 部門協助：
- 允許執行未簽章的應用程式
- 開放特定端口
- 加入本機系統管理員群組

---

## ✅ 部署前檢查清單

執行以下命令，確認環境正確：

```powershell
# 1. 確認以系統管理員身分執行
[Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains 'S-1-5-32-544'

# 2. 檢查執行政策
Get-ExecutionPolicy

# 3. 檢查防火牆狀態
Get-NetFirewallProfile | Format-Table Name, Enabled

# 4. 檢查 Node.js
node --version
npm --version

# 5. 檢查 Oracle 服務
Get-Service | Where-Object {$_.Name -like "*Oracle*" -and $_.Status -eq "Running"}
```

---

## 🆘 快速排解腳本

複製以下腳本並另存為 `fix-security.ps1`，以系統管理員身分執行：

```powershell
# Windows Server 安全設定自動修復腳本

Write-Host "PMS API - Windows 安全設定修復工具" -ForegroundColor Green
Write-Host "=========================================`n"

# 1. 設定執行政策
Write-Host "[1/5] 設定 PowerShell 執行政策..."
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
Write-Host "✅ 完成`n"

# 2. 加入 Defender 排除
Write-Host "[2/5] 加入 Windows Defender 排除清單..."
Add-MpPreference -ExclusionPath "C:\KTW-bot" -ErrorAction SilentlyContinue
Add-MpPreference -ExclusionPath "C:\Program Files\nodejs" -ErrorAction SilentlyContinue
Write-Host "✅ 完成`n"

# 3. 解除檔案封鎖
Write-Host "[3/5] 解除檔案封鎖..."
if (Test-Path "C:\KTW-bot\pms-api-poc") {
    Get-ChildItem "C:\KTW-bot\pms-api-poc" -Recurse | Unblock-File -ErrorAction SilentlyContinue
    Write-Host "✅ 完成`n"
} else {
    Write-Host "⚠️  找不到專案目錄`n" -ForegroundColor Yellow
}

# 4. 設定防火牆規則
Write-Host "[4/5] 設定防火牆規則..."
New-NetFirewallRule -DisplayName "PMS API Port 3000" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
Write-Host "✅ 完成`n"

# 5. 檢查 Oracle 服務
Write-Host "[5/5] 檢查 Oracle 服務..."
$oracleServices = Get-Service | Where-Object {$_.Name -like "*Oracle*"}
if ($oracleServices) {
    $oracleServices | Format-Table Name, Status -AutoSize
} else {
    Write-Host "⚠️  找不到 Oracle 服務" -ForegroundColor Yellow
}

Write-Host "`n========================================="
Write-Host "✅ 安全設定完成！" -ForegroundColor Green
Write-Host "=========================================`n"
```

---

**完成安全設定後，繼續執行 [DEPLOY_WINDOWS.md](DEPLOY_WINDOWS.md) 中的部署步驟。**
