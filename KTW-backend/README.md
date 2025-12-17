# Backend API 模組

> KTW Hotel 後端 API 服務 - 中間層通訊與通知系統

---

## �� 模組概述

Backend API 是 KTW Hotel 系統的中間層服務,負責處理 Admin Dashboard 與 PMS API 之間的通訊,以及 LINE Bot 的即時訊息推送。

### 核心功能
- ✅ PMS API 代理與快取
- ✅ WebSocket 即時通訊
- ✅ LINE Bot 訊息推送
- ✅ 訂單自動匹配驗證 (PMS 整合)
- ✅ 服務狀態監控
- ✅ CORS 處理

---

## 🏗️ 技術架構

### 技術棧
- **語言**: Node.js
- **框架**: Express.js
- **即時通訊**: WebSocket (ws)
- **HTTP 客戶端**: Axios

---

## 🚀 快速開始

### 環境需求
- Node.js 16+

### 安裝依賴
```bash
cd KTW-backend
npm install
```

### 啟動服務
```bash
npm start
# 或使用 PM2
pm2 start ecosystem.config.js --only DT-Backend
```

---

## 📝 版本資訊

- **當前版本**: v1.0.1
- **最後更新**: 2025-12-17
- **維護者**: KTW Hotel IT Team

詳細變更記錄請參閱 [CHANGELOG.md](./CHANGELOG.md)
