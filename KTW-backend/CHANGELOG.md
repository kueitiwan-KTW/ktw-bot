# Backend API - Changelog

> 後端 API 服務的詳細變更記錄

---

## [1.0.1] - 2025-12-17

### ✨ 新功能
- **已 KEY 訂單驗證 API**
  - 更新 `PATCH /api/pms/same-day-bookings/:order_id/checkin`
  - 新增 PMS 交叉驗證邏輯：查詢 PMS 今日入住名單
  - **自動匹配**：比對電話號碼後 9 碼
  - **狀態處理**：
    - 匹配成功：標記為 `checked_in`
    - 匹配失敗：標記為 `mismatch` (KEY 錯)，返回錯誤訊息供前端顯示

### 🔗 整合更新
- 整合 PMS API 新增的 `/mismatch` 端點
- 統一錯誤處理回傳格式

---

## [1.0.0] - 2025-12-10

### 初始版本
- Express.js 基礎架構
- 通知推送端點
- 服務狀態監控
- WebSocket 支援
