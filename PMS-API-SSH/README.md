# PMS Server SSH 遠端連線設定

> 適用於 Windows Server 2016

本資料夾包含用於啟用/停用 PMS 伺服器 SSH 連線的 PowerShell 腳本。

---

## 🔑 SSH 金鑰連線（免密碼）

> ⚠️ **重要提示**：本連線使用 **SSH 金鑰認證**，**不需要輸入密碼**！  
> 如果系統要求密碼，表示金鑰設定有問題，請執行 `Fix-SSH-KeyAuth.ps1` 修正。

### 快速連線指令

**直接連線**（免密碼）：
```bash
ssh Administrator@192.168.8.3
```

**遠端執行指令**：
```bash
# 範例：檢查服務狀態
ssh Administrator@192.168.8.3 "Get-Service pms-api"

# 範例：重啟 PMS API
ssh Administrator@192.168.8.3 "Restart-Service pms-api"

# 範例：執行 Node.js 腳本
ssh Administrator@192.168.8.3 "cd C:\pms-api && node test.js"
```

### 金鑰位置

- **Mac 端私鑰**：`~/.ssh/id_rsa`（已設定）
- **Windows Server 公鑰**：`C:\ProgramData\ssh\administrators_authorized_keys`

---

## 📁 檔案說明

| 檔案 | 功能 |
|------|------|
| `Enable-SSH.ps1` | 安裝並啟用 OpenSSH Server + 設定防火牆 |
| `Disable-SSH.ps1` | 停止 SSH 服務 + 關閉防火牆（安全用途） |
| `Check-SSH-Status.ps1` | 檢查目前 SSH 服務狀態 |
| `Fix-SSH-KeyAuth.ps1` | 修正金鑰認證 + 設定 Mac 公鑰 |

---

## 🚀 首次設定步驟

### 步驟 1：複製到 PMS 伺服器

將整個 `PMS-API-SSH` 資料夾複製到 Windows Server 上：
```
C:\KTW-bot\PMS-API-SSH
```

### 步驟 2：啟用 SSH（如未啟用）

1. **右鍵點擊** `Enable-SSH.ps1`
2. 選擇 **「以 PowerShell 執行」**

### 步驟 3：設定金鑰認證

1. **右鍵點擊** `Fix-SSH-KeyAuth.ps1`
2. 選擇 **「以系統管理員身分執行」**

---

## 🔒 安全建議

1. **不使用時停用 SSH**：執行 `Disable-SSH.ps1` 關閉連線
2. **使用強密碼**：確保 Windows 帳號密碼夠強
3. **限制連線 IP**：可在防火牆進階設定中限制來源 IP

---

## ❓ 常見問題

### 連線逾時 (Operation timed out)

1. 確認 SSH 服務已啟動：執行 `Check-SSH-Status.ps1`
2. 確認防火牆已開放 Port 22
3. 確認兩台電腦在同一網段

### 密碼錯誤 / 金鑰不工作

- 重新執行 `Fix-SSH-KeyAuth.ps1`
- 確認 SSH 服務已重啟

---

*最後更新：2025-12-15*

