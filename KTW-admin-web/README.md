# Admin Dashboard 模組

> KTW Hotel 管理後台 - 即時監控與管理系統

---

## 📋 模組概述

Admin Dashboard 是 KTW Hotel 的管理後台系統,提供即時的 PMS 數據監控、客人資訊管理和服務狀態追蹤。

### 核心功能
- ✅ 即時 PMS 數據顯示 (今日入住/退房、住房率、空房數)
- ✅ 入住客人列表與詳細資訊
- ✅ 房況即時監控
- ✅ 服務狀態監控 (Gmail, AI, PMS)
- ✅ LINE Bot 訊息推送顯示
- ✅ VIP 客戶標記

---

## 🏗️ 技術架構

### 技術棧
- **前端框架**: Vue.js 3 (Composition API)
- **建構工具**: Vite
- **UI 元件**: GridStack (拖拽式佈局)
- **樣式**: Vanilla CSS
- **後端通訊**: WebSocket + REST API

### 系統架構
```
Vue.js 3 Frontend
    ↓
Backend API (Node.js)
    ↓
PMS API (Oracle Database)
```

---

## 📁 檔案結構

```
KTW-admin-web/
├── README.md                    ← 本文件
├── CHANGELOG.md                 ← 版本變更記錄
├── package.json                 ← 專案配置
├── vite.config.js               ← Vite 配置
├── index.html                   ← HTML 入口
├── src/
│   ├── App.vue                  ← 主應用元件
│   ├── main.js                  ← 應用入口
│   ├── style.css                ← 全域樣式
│   └── components/
│       └── GuestCard.vue        ← 客人資訊卡片元件
└── public/                      ← 靜態資源
```

---

## 🚀 快速開始

### 環境需求
- Node.js 16+
- npm 或 yarn

### 安裝依賴
```bash
cd KTW-admin-web
npm install
```

### 開發模式
```bash
npm run dev
```
訪問: `http://localhost:5173`

### 生產建置
```bash
npm run build
```

### 使用 PM2 部署
```bash
pm2 start ecosystem.config.js --only DT-Admin-Web
```

---

## 📊 功能模組

### 1. PMS 數據監控
- **今日入住**: 實時顯示今日入住人數
- **今日退房**: 實時顯示今日退房人數
- **住房率**: 當前住房率百分比
- **空房數**: 可用房間數量
- **更新頻率**: 15 秒

### 2. 入住客人列表
- **顯示資訊**: 姓名、房號、房型、入住日期、訂單來源
- **LINE 姓名**: 顯示 LINE 用戶名稱 (如有)
- **展開詳情**: 點擊卡片查看完整資訊
- **更新頻率**: 30 秒

### 3. 房況監控
- **房間狀態**: 空房、已住、維修中
- **房型分佈**: 各房型數量統計
- **更新頻率**: 15 秒

### 4. 服務狀態
- **Gmail 連線**: 監控 Gmail API 狀態
- **AI 服務**: 監控 Gemini AI 狀態
- **PMS 連線**: 監控 PMS API 狀態
- **更新頻率**: 5 秒

### 5. 即時訊息推送
- **來源**: LINE Bot 新訊息
- **顯示**: 用戶名稱、頭像、訊息內容、VIP 標記
- **通知**: 桌面通知 (需授權)

### 6. 訂單自動驗證 (New)
- **已 KEY 匹配**: 自動比對 PMS 今日入住名單 (電話後 9 碼)
- **狀態顯示**: 支援 KEY 錯 (Mismatch)、已 KEY (Checked In)、待入住 (Pending)
- **異常處理**: 提供重新匹配按鈕，方便資料修正後再次驗證

---

## 🎨 UI 特色

### GridStack 拖拽佈局
- 可自由拖拽調整區塊位置
- 可調整區塊大小
- 響應式設計,自動適應螢幕

### 自動更新倒數
- 顯示下次更新剩餘秒數
- 30 秒倒數計時器
- 手動刷新按鈕

### 客人卡片展開
- 點擊卡片展開詳細資訊
- 獨立展開,不影響其他卡片
- 平滑動畫效果

---

## 🔧 開發指南

### 修改更新頻率
編輯 `src/App.vue`:
```javascript
const REFRESH_INTERVALS = {
  serviceStatus: 5000,    // 服務狀態: 5秒
  pmsStats: 15000,        // PMS 統計: 15秒
  guestList: 30000,       // 客人列表: 30秒
  roomStatus: 15000       // 房況: 15秒
}
```

### 新增元件
1. 在 `src/components/` 建立新元件
2. 在 `App.vue` 中引入
3. 更新 `CHANGELOG.md`

### 修改樣式
編輯 `src/style.css`,遵循現有的 CSS 變數系統

---

## 🔗 相關文檔

- [CHANGELOG.md](./CHANGELOG.md) - 版本變更記錄
- [DEVELOPMENT_SOP.md](../docs/DEVELOPMENT_SOP.md) - 開發標準作業程序

---

## 🐛 故障排除

### Dashboard 無法載入
```bash
# 檢查 Backend API 狀態
curl http://localhost:3000/api/health

# 檢查 PM2 服務
pm2 list

# 重啟服務
pm2 restart DT-Admin-Web
```

### 數據不更新
1. 檢查 PMS API 連線
2. 檢查瀏覽器 Console 錯誤
3. 清除瀏覽器快取

---

## 📝 版本資訊

- **當前版本**: v1.4.0
- **最後更新**: 2025-12-21
- **維護者**: KTW Hotel IT Team

詳細變更記錄請參閱 [CHANGELOG.md](./CHANGELOG.md)
