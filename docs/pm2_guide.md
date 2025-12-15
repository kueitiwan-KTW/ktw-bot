# PM2 服務管理指南 (Process Manager 2)

本專案使用 PM2 來管理所有後端與前台服務，確保即使關閉終端機或 SSH 連線，服務仍能在背景持續運行 (Daemon Mode)。

## 1. 快速啟動 (Quick Start)

如果您沒有全域安裝 PM2，請使用 `npx` 指令：

```bash
# 啟動所有服務 (Backend, PMS API, Admin, Bot, Ngrok)
cd /Users/ktw/KTW-bot
npx pm2 start ecosystem.config.js
```

成功啟動後，您會看到一個表格列出所有運作中的服務 (Status: online)。

---

## 2. 常用管理指令

| 動作 | 指令 | 說明 |
|:---|:---|:---|
| **查看狀態** | `npx pm2 list` | 列出目前所有服務的 CPU/記憶體使用量與狀態。 |
| **停止服務** | `npx pm2 stop all` | 停止所有服務運作。 |
| **重啟服務** | `npx pm2 restart all` | 重新啟動所有服務 (更新程式碼後使用)。 |
| **查看日誌** | `npx pm2 logs` | 即時監看所有服務的 Console 輸出 (除錯用)。 |
| **刪除服務** | `npx pm2 delete all` | 停止並從清單中移除所有服務。 |

---

## 3. 服務架構說明 (ecosystem.config.js)

`ecosystem.config.js` 定義了以下服務：

1.  **DT-Backend** (Port 3000): Node.js 後端核心。
2.  **PMS-API** (Port 3005): Oracle PMS 資料介接 API。
3.  **DT-Admin-Web** (Port 5002): Vue.js 管理後台。
4.  **Line-Bot-Py**: Python LINE Bot 主程式。
5.  **Ngrok-Tunnel** (Port 5001 -> Public): 讓外部 LINE Server 能呼叫本地 Bot。

---

## 4. 全域安裝 PM2 (選擇性)

若您覺得每次都要打 `npx` 很麻煩，可以執行以下指令進行全域安裝：

```bash
npm install -g pm2
```
安裝後，上述指令中的 `npx pm2` 即可簡化為 `pm2`。
