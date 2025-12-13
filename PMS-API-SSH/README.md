# PMS Server SSH 遠端連線設定

> 適用於 Windows Server 2016

本資料夾包含用於啟用/停用 PMS 伺服器 SSH 連線的 PowerShell 腳本。

---

## 📁 檔案說明

| 檔案 | 功能 |
|------|------|
| `Enable-SSH.ps1` | 安裝並啟用 OpenSSH Server + 設定防火牆 |
| `Disable-SSH.ps1` | 停止 SSH 服務 + 關閉防火牆（安全用途） |
| `Check-SSH-Status.ps1` | 檢查目前 SSH 服務狀態 |

---

## 🚀 使用方式

### 步驟 1：複製到 PMS 伺服器

將整個 `PMS-API-SSH` 資料夾複製到 Windows Server 上（例如桌面）。

### 步驟 2：啟用 SSH

1. **右鍵點擊** `Enable-SSH.ps1`
2. 選擇 **「以 PowerShell 執行」**
3. 如果出現權限提示，選擇 **「是」**

> ⚠️ 必須以**系統管理員**身分執行！

### 步驟 3：確認連線資訊

腳本執行完成後會顯示：
- 伺服器 IP 位址
- 連線 Port (22)
- 建議的連線指令

---

## 🔌 從 Mac 連線

啟用成功後，使用以下指令連線：

```bash
ssh 使用者名稱@192.168.8.3
```

例如：
```bash
ssh Administrator@192.168.8.3
ssh ktw@192.168.8.3
```

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

### 密碼錯誤

- 使用 Windows 登入帳號密碼
- 帳號名稱區分大小寫

### 首次連線出現警告

這是正常的，輸入 `yes` 繼續即可：
```
The authenticity of host '192.168.8.3' can't be established.
Are you sure you want to continue connecting (yes/no)? yes
```
