# PMS API POC 部署檢查表

> **目標**：在 Windows Server (192.168.8.3) 上部署 Oracle PMS API POC

---

## 📦 準備工作

### Mac 端
- [x] 已打包部署檔案：`pms-api-poc-deploy.tar.gz` (1.3MB)
- [x] 檔案位置：`/Users/ktw/KTW-bot/pms-api-poc-deploy.tar.gz`

### 檔案傳輸方式
選擇以下任一方式將檔案傳到 Windows Server：

**方式 A：網路共享**
```bash
# Mac 端
scp pms-api-poc-deploy.tar.gz administrator@192.168.8.3:C:/
```

**方式 B：USB 隨身碟**
- 複製 `pms-api-poc-deploy.tar.gz` 到隨身碟
- 插入 Windows Server
- 解壓縮到 `C:\KTW-bot\`

**方式 C：遠端桌面**
- 連線到 Windows Server
- 使用遠端桌面的檔案傳輸功能

---

## 🖥️ Windows Server 部署步驟

### 步驟 0：解壓縮檔案
```powershell
# 如果使用 .tar.gz，需要安裝 7-Zip 或 WinRAR
# 建議直接將 pms-api-poc 資料夾複製過去
```

### 步驟 1：以系統管理員身分執行 PowerShell
1. 按 `Win + X`
2. 選擇「Windows PowerShell (系統管理員)」

### 步驟 2：執行安全設定腳本
```powershell
cd C:\KTW-bot\pms-api-poc
.\fix-security.ps1
```

**預期結果**：
```
[1/5] 設定 PowerShell 執行政策...
✅ 完成

[2/5] 加入 Windows Defender 排除清單...
✅ 完成
  ✓ C:\KTW-bot 已加入排除清單

[3/5] 解除檔案封鎖...
✅ 完成

[4/5] 設定防火牆規則...
✅ 完成 (已開放 Port 3000)

[5/5] 檢查 Oracle 服務...
Name                     Status  DisplayName
----                     ------  -----------
OracleServiceGDWUUKT     Running Oracle Database Service
...

✅ 安全設定完成！
```

### 步驟 3：安裝 Node.js（如果尚未安裝）
1. 開啟瀏覽器前往：https://nodejs.org/
2. 下載並安裝 LTS 版本（v20.10.0）
3. 驗證安裝：
   ```powershell
   node --version
   npm --version
   ```

### 步驟 4：安裝 npm 套件
```powershell
cd C:\KTW-bot\pms-api-poc
npm install
```

**預期結果**：
```
added 2 packages, and audited 3 packages

found 0 vulnerabilities
```

### 步驟 5：配置環境變數
```powershell
# 編輯 .env 檔案
notepad .env
```

**設定內容**：
```env
# Oracle 資料庫連線設定（使用 OS 驗證）
DB_CONNECT_STRING=localhost:1521/gdwuukt

# 測試訂單編號（填入實際存在的訂單號）
TEST_ORDER_ID=00150501
```

### 步驟 6：執行 POC 測試

**測試 1：連線測試**
```powershell
npm test
```

**預期結果**：
```
🔌 正在連接 Oracle 資料庫...
   驗證方式: OS 驗證（Operating System Authentication）
   連線字串: localhost:1521/gdwuukt

✅ 連線成功！

📊 測試查詢資料庫版本...
   版本: Oracle Database 12c Enterprise Edition Release 12.2.0

🎉 POC 測試成功！資料庫連線沒問題。
```

**測試 2：訂單查詢測試**
```powershell
npm run test-query
```

**預期結果**：
```
✅ 找到訂單資料：

   訂單編號: 00150501
   訂房人: XXX
   聯絡電話: 0912XXXXXX
   入住日期: 2025-12-15
   退房日期: 2025-12-17
   住宿天數: 2 晚
   訂單狀態: O

📦 查詢房型資料...

   房型 1: 雙人房
   房間數: 1 間
   成人數: 2 人
   兒童數: 0 人

🎉 POC 驗證成功！
```

---

## 💻 Mac 端測試

### 步驟 7：測試 API 連線（在 Mac 上執行）

```bash
cd /Users/ktw/KTW-bot/pms-api-poc
python3 test-api-client.py
```

**如果測試失敗**：
- 請先在 Windows Server 上建立完整的 REST API 服務
- POC 測試只驗證 Oracle 連線，尚未建立 HTTP API

---

## ✅ 成功標準

POC 測試成功的標準：

### Windows Server 端
- [x] Node.js 已安裝
- [x] 安全設定完成（Defender、防火牆、執行政策）
- [x] npm 套件安裝成功
- [x] Oracle 連線測試成功
- [x] 訂單查詢測試成功
- [x] 資料格式正確（有訂房人、日期、房型）

### 驗證項目
- [ ] 可以查詢到訂單資料
- [ ] 訂房人姓名正確（不是空白或幻覺）
- [ ] 入住日期正確
- [ ] 房型資訊正確
- [ ] 回應時間 < 1 秒

---

## 🚨 故障排除

### 錯誤 1：ORA-01017（使用者名稱/密碼無效）
**原因**：OS 驗證設定問題

**解決**：
```powershell
# 1. 確認是在 Windows Server 本機執行
# 2. 確認登入的 Windows 帳號有 ORA_DBA 群組權限
net localgroup ORA_DBA

# 3. 如果沒有，加入群組（需系統管理員）
net localgroup ORA_DBA YourUsername /add

# 4. 登出再登入
```

### 錯誤 2：ORA-12560（TNS: protocol adapter error）
**原因**：Oracle 服務未啟動

**解決**：
```powershell
# 啟動 Oracle 服務
net start OracleServiceGDWUUKT
net start OracleOraDB12Home1TNSListener

# 驗證
Get-Service | Where-Object {$_.Name -like "*Oracle*"}
```

### 錯誤 3：npm install 失敗
**原因**：Windows Defender 阻擋

**解決**：
```powershell
# 重新執行安全設定腳本
.\fix-security.ps1

# 手動加入排除
Add-MpPreference -ExclusionPath "C:\KTW-bot"
```

---

## 📝 測試成功後回報

請回報以下資訊：

1. ✅ 連線測試結果（成功/失敗）
2. ✅ 訂單查詢測試結果（成功/失敗）
3. ✅ 查詢到的訂單資料是否正確
4. ✅ 是否有遇到任何錯誤

**測試成功後，我們將進行：**
1. 建立完整的 REST API 服務（5 個端點）
2. 部署並測試 API
3. 整合到 LINE BOT
4. 解決幻覺問題

---

**準備好了嗎？開始部署吧！** 🚀
