# Windows Server 部署指南 - PMS API

> **目標**：在 Windows Server（192.168.8.3）上部署 PMS REST API

---

## 📋 部署前準備

### 系統資訊
- **伺服器 IP**：192.168.8.3
- **作業系統**：Windows Server
- **Oracle 資料庫**：已安裝（gdwuukt）
- **驗證方式**：OS 驗證（Operating System Authentication）

---

## ⚠️ Windows 安全設定（重要！）

### 1. Windows Defender 排除項目

**問題**：Windows Defender 可能會阻擋 Node.js 或 npm 套件

**解決方法**：
```powershell
# 以系統管理員身分執行 PowerShell

# 加入排除資料夾
Add-MpPreference -ExclusionPath "C:\KTW-bot"
Add-MpPreference -ExclusionPath "C:\Program Files\nodejs"

# 驗證排除清單
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### 2. 防火牆設定

**問題**：防火牆可能阻擋 API 端口（通常是 3000 或 8000）

**解決方法**：
```powershell
# 允許入站連線到 API 端口
New-NetFirewallRule -DisplayName "PMS API" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### 3. PowerShell 執行政策

**問題**：無法執行 .bat 或 PowerShell 腳本

**解決方法**：
```powershell
# 檢查目前政策
Get-ExecutionPolicy

# 如果顯示 "Restricted"，執行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. 檔案解除封鎖

**問題**：從網路下載的檔案可能被標記為不安全

**解決方法**：
```powershell
# 解除封鎖所有專案檔案
cd C:\KTW-bot\pms-api-poc
Get-ChildItem -Recurse | Unblock-File
```

或手動操作：
1. 右鍵點擊檔案 → 內容
2. 勾選「解除封鎖」
3. 點擊「套用」

### 5. Oracle 連線檢查

**確認 Oracle 服務正在運行**：
```powershell
# 檢查服務狀態
Get-Service | Where-Object {$_.Name -like "*Oracle*"} | Format-Table Name, Status

# 如果未運行，啟動服務
net start OracleServiceGDWUUKT
net start OracleOraDB12Home1TNSListener
```

---

## 🚀 部署步驟

### 步驟 1：安裝 Node.js

1. **下載 Node.js**
   - 前往：https://nodejs.org/
   - 下載 LTS 版本（Windows Installer .msi）
   - 推薦：v20.10.0 或更新版本

2. **安裝**
   ```powershell
   # 執行下載的安裝程式
   # 選擇：Add to PATH
   # 選擇：Install Native Modules Tools (如果需要)
   ```

3. **驗證安裝**
   ```powershell
   node --version
   npm --version
   ```

---

### 步驟 2：複製專案檔案

**方式 A：使用 Git（推薦）**
```powershell
# 1. 安裝 Git for Windows (如果還沒有)
# 下載：https://git-scm.com/download/win

# 2. Clone 專案
cd C:\
git clone https://github.com/kueitiwan-KTW/KTW-bot.git
cd KTW-bot\pms-api-poc
```

**方式 B：手動複製**
```powershell
# 1. 建立目錄
mkdir C:\KTW-bot\pms-api-poc
cd C:\KTW-bot\pms-api-poc

# 2. 複製以下檔案到此目錄：
#    - package.json
#    - test-connection.js
#    - test-query.js
#    - .env.example
```

---

### 步驟 3：安裝依賴套件

```powershell
cd C:\KTW-bot\pms-api-poc
npm install
```

---

### 步驟 4：配置環境變數

1. **建立 .env 檔案**
   ```powershell
   copy .env.example .env
   notepad .env
   ```

2. **編輯 .env 內容**
   ```env
   # Oracle 資料庫連線設定（使用 OS 驗證）
   DB_CONNECT_STRING=localhost:1521/gdwuukt
   
   # 測試訂單編號
   TEST_ORDER_ID=00150501
   ```
   
   > **重要**：因為在同一台伺服器上，使用 `localhost` 即可

---

### 步驟 5：執行測試

```powershell
# 測試 1：資料庫連線
npm test

# 預期結果：
# ✅ 連線成功
# ✅ 顯示 Oracle 版本
```

```powershell
# 測試 2：查詢訂單
npm run test-query

# 預期結果：
# ✅ 查到訂單資料
# ✅ 顯示訂房人、日期、房型
```

---

## 🔧 常見問題排解

### 問題 1：npm 不是內部或外部命令
**原因**：環境變數未設定
**解決**：
```powershell
# 手動加入 PATH
setx PATH "%PATH%;C:\Program Files\nodejs"
# 重新開啟 PowerShell
```

### 問題 2：ORA-12560: TNS:protocol adapter error
**原因**：Oracle 服務未啟動
**解決**：
```powershell
# 啟動 Oracle 服務
net start OracleServiceGDWUUKT
net start OracleOraDB12Home1TNSListener
```

### 問題 3：權限不足
**原因**：未以系統管理員執行
**解決**：右鍵 PowerShell → 以系統管理員身分執行

---

## 📦 下一步：建立完整 API 服務

測試成功後，執行以下步驟建立完整的 REST API：

1. **建立 Express API 專案**
   ```powershell
   cd C:\KTW-bot
   mkdir pms-api
   cd pms-api
   npm init -y
   npm install express oracledb dotenv cors
   ```

2. **複製 API 程式碼**
   - 參考 `docs/pms_api_specification.md`
   - 實作 5 個 REST API 端點

3. **設定 Windows 服務**
   ```powershell
   # 安裝 PM2（Node.js 程序管理器）
   npm install -g pm2
   npm install -g pm2-windows-service
   
   # 安裝為 Windows 服務
   pm2-service-install
   
   # 啟動 API
   pm2 start server.js --name pms-api
   pm2 save
   ```

---

## 📝 檢查清單

- [ ] Node.js 已安裝並驗證
- [ ] 專案檔案已複製到伺服器
- [ ] npm 依賴已安裝
- [ ] .env 檔案已配置
- [ ] 連線測試成功（npm test）
- [ ] 訂單查詢測試成功（npm run test-query）
- [ ] 準備建立完整 API 服務

---

## 🆘 需要協助？

如果遇到問題，請提供：
1. 錯誤訊息完整內容
2. 執行的指令
3. Windows Server 版本

---

**部署完成後，您就可以：**
- ✅ 從 LINE BOT 呼叫此 API
- ✅ 查詢即時訂單資料
- ✅ 停用 Gmail API
- ✅ 解決 BOT 幻覺問題
