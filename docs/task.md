# NEC SL2100 AI 語音訂房系統整合專案

## 目標
在現有的 NEC SL2100 電話系統上實現 AI 自動接聽與訂房服務功能。

## 任務清單

### 研究與規劃階段
- [x] 研究 NEC SL2100 整合方式（SIP、API、自動總機功能）
- [x] 研究 AI 語音助理解決方案（Google Dialogflow、Twilio、Asterisk 等）
- [x] 設計系統架構與資料流
- [x] 確認訂房系統需求與資料格式（已確認有 PMS 但暫時無法存取）
- [x] 更新實作計畫文件（已調整為過渡方案）

### PMS 資料擷取階段（優先處理）
- [x] 研究德安資訊 PMS 系統架構
- [x] 探勘資料庫類型與位置（Oracle 12.2.0, SID: gdwuukt）
- [x] 取得資料庫存取權限
- [x] 分析資料庫結構（ORDER_MN, ORDER_DT, ROOM_RF, ROOM_MN, RMINV_MN）
- [x] 建立資料擷取介面（API 規格設計完成）

### PMS API 開發階段
- [ ] 建立 Node.js + Express 專案
- [ ] 實作查詢訂單 API（GET /api/bookings/search）
- [ ] 實作訂單詳情 API（GET /api/bookings/:id）
- [ ] 實作查詢可用房間 API（GET /api/rooms/availability）
- [ ] 實作建立訂單 API（POST /api/bookings）
- [ ] 實作取消訂單 API（DELETE /api/bookings/:id）
- [ ] API 測試與除錯
- [ ] 部署到 Windows Server

### LINE BOT 整合階段
- [ ] 調整 check_order_status 函式（使用 PMS API）
- [ ] 測試 BOT 查詢功能
- [ ] 建立 Fallback 機制（API 故障時使用 Gmail）

### Next.js 後台開發階段
- [ ] 初始化 Next.js + TypeScript 專案
- [ ] 實作訂單管理頁面
- [ ] 實作房況總覽頁面
- [ ] 實作 BOT 監控頁面
- [ ] 串接 PMS API
- [ ] 部署後台（Vercel 或自架）

### 技術方案設計
- [ ] 選擇合適的 AI 語音平台
- [ ] 設計對話流程（問候 → 確認需求 → 收集訂房資訊 → 確認 → 記錄）
- [ ] 規劃與 NEC SL2100 的整合方式
- [ ] 設計訂房資料庫結構

### 實作階段
- [ ] 設置 AI 語音助理
- [ ] 配置 NEC SL2100 整合
- [ ] 開發訂房資料處理邏輯
- [ ] 建立訂房記錄系統

### 測試與驗證
- [ ] 測試電話接聽流程
- [ ] 測試訂房對話流程
- [ ] 驗證資料記錄正確性
- [ ] 使用者驗收測試
