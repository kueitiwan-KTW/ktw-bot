# KTW Hotel System

> KTW 旅館自動化管理系統 (Monorepo)

本專案整合了 LINE Bot 智能客服、PMS 系統串接、Admin 管理後台與後端 API 服務，打造全方位的旅館自動化解決方案。

---

## 🏗️ 系統模組

本專案採用 Monorepo 架構，包含以下核心模組：

### 1. [LINE Bot](./LINEBOT/README.md) 🤖
- **功能**: 24/7 智能客服機
- **技術**: Python, Flask, Google Gemini AI
- **亮點**: 語音轉文字、多房型當日預訂、圖片訂單識別

### 2. [Admin Dashboard](./KTW-admin-web/README.md) 🖥️
- **功能**: 櫃台人員操作介面
- **技術**: Vue.js 3, Vite
- **亮點**: 即時房況監控、已 KEY 訂單自動驗證、服務狀態儀表板

### 3. [Backend API](./KTW-backend/README.md) ⚙️
- **功能**: 中間層通訊與通知服務
- **技術**: Node.js, Express, WebSocket
- **亮點**: 統一 API Gateway、LINE 訊息即時推送

### 4. [PMS API](./pms-api/README.md) 🗄️
- **功能**: Oracle PMS 資料庫介面
- **技術**: Node.js, oracledb
- **亮點**: 舊系統 API 化、訂單查詢與狀態回寫

---

## 🚀 快速導覽

### 開發規範
- [開發標準作業程序 (SOP)](./docs/DEVELOPMENT_SOP.md) - **⚠️ 修改程式前必讀**
- [API 整合指南](./docs/KTW_BOT_INTEGRATION_GUIDE.md)
- [PMS 資料庫參考](./pms-api/PMS-DATABASE-REFERENCE.md)

### 版本歷史
- [總體 CHANGELOG](./CHANGELOG.md)
- [LINE Bot 變更](./LINEBOT/CHANGELOG.md)
- [Admin Web 變更](./KTW-admin-web/CHANGELOG.md)
- [Backend API 變更](./KTW-backend/CHANGELOG.md)
- [PMS API 變更](./pms-api/CHANGELOG.md)

---

## 🛠️ 環境設置

### 全局需求
- Node.js v16+ (建議 v18 LTS)
- Python 3.9+
- Git

### 啟動開發環境
每個模組皆可獨立啟動，請參考各模組的 README。

```bash
# 啟動 PM2 管理所有服務
pm2 start ecosystem.config.js
```

---

## 📝 維護資訊
- **維護者**: KTW Hotel IT Team
- **最新版本**: v1.2.0 (System-wide)
- **最後更新**: 2025-12-17
