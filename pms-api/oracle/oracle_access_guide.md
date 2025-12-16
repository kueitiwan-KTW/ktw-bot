# Oracle PMS 資料庫存取操作指引

## 目標
協助您即時取得德安資訊 PMS（Oracle 資料庫）的存取權限。

---

## 第一步：確認 Oracle 環境

請在您的 **Windows Server 2016** 上執行以下指令：

### 1. 開啟命令提示字元（以系統管理員身分）
- 按 `Win + X`
- 選擇「命令提示字元（系統管理員）」或「PowerShell（系統管理員）」

### 2. 檢查 Oracle 服務狀態

```cmd
sc query OracleService*
```

**或使用 PowerShell**：
```powershell
Get-Service | Where-Object {$_.Name -like "*Oracle*"}
```

### 3. 找到 Oracle 安裝目錄

```cmd
echo %ORACLE_HOME%
```

如果沒有顯示，請執行：
```cmd
dir /s /b C:\app\oracle*.exe
dir /s /b D:\app\oracle*.exe
```

### 📋 請將上述指令的執行結果貼給我

---

## 第二步：連接 Oracle（待確認後提供）

根據您的執行結果，我會提供對應的連線指令。

**可能的情況**：
- **情況 A**：使用 Windows 驗證（OS Authentication）
- **情況 B**：重設 SYS/SYSTEM 密碼
- **情況 C**：透過 SQL*Plus 直接連線

---

## 第三步：探索資料庫結構（待連線後進行）

連線成功後，我會提供 SQL 查詢指令來：
1. 列出所有資料表
2. 找出訂房相關的表格
3. 分析資料結構

---

## 常見 Oracle 連線方式預覽

### 方式 1：使用 OS 驗證（推薦）
```cmd
sqlplus / as sysdba
```
> 前提：您的 Windows 帳號需在 `ORA_DBA` 群組中

### 方式 2：使用帳號密碼
```cmd
sqlplus system/password@database_name
```

### 方式 3：使用 SQL Developer（圖形介面）
如果您偏好圖形介面，可以使用 Oracle SQL Developer

---

## ⚠️ 注意事項

1. **備份優先**：建議先備份資料庫
2. **離峰操作**：建議在 PMS 離峰時段操作
3. **記錄操作**：建議將每個步驟的結果截圖或記錄

---

## 現在請執行「第一步」的指令，並將結果告訴我！
