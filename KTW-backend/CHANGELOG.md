# Backend API - Changelog

> 後端# KTW Backend Changelog

## [1.6.0] - 2025-12-21
### ✨ 新功能：用戶訂單關聯 (方案 D)
**檔案**: `src/helpers/db.js`, `src/index.js`
- **新資料表**: `user_order_mapping` 記錄 LINE 用戶與訂單的對應關係
- **API 端點**:
  - `GET /api/user-orders/:userId` - 取得用戶訂單列表
  - `GET /api/user-orders/:userId/latest` - 取得用戶最近訂單
  - `POST /api/user-orders` - 儲存用戶訂單關聯

## [1.5.0] - 2025-12-21
### ✨ 新功能：OTA/PMS 雙重匹配機制 (方案 A)
**檔案**: `src/index.js` (L90-110, L139-145)
- **問題**: 當 Bot 資料存在 OTA ID 下，後端用 PMS ID 查詢會找不到
- **修復**: `processBookings` 現在同時收集 PMS ID、完整 OTA ID、純數字 OTA
- **搜索順序**: OTA ID → 純數字 OTA → PMS ID
- **影響**: 林宛錡等案例資料現可正確顯示 LINE 姓名與需求

## [1.4.0] - 2025-12-20

### ✨ 新功能：Bot Session 持久化 (Session Persistence)

#### 1. 資料庫層 (SQLite)
**檔案**: `src/helpers/db.js` (L111-215)
- **新增資料表**: `bot_sessions`
  ```sql
  CREATE TABLE bot_sessions (
      user_id TEXT PRIMARY KEY,
      handler_type TEXT,      -- 'order_query', 'same_day_booking', etc.
      state TEXT,             -- 狀態字串
      data TEXT,              -- JSON 格式流程資料
      pending_intent TEXT,    -- 排隊意圖
      pending_intent_message TEXT,
      created_at DATETIME,
      updated_at DATETIME
  );
  ```
- **新增函數**: 
  - `getBotSession(userId)` - 讀取 session
  - `updateBotSession(userId, data)` - 更新 session
  - `deleteBotSession(userId)` - 刪除 session

#### 2. API 端點
**檔案**: `src/index.js` (L799-850)
| 方法 | 端點 | 說明 |
|-----|------|------|
| GET | `/api/bot/sessions/:userId` | 取得 Bot Session |
| PUT | `/api/bot/sessions/:userId` | 更新 Bot Session |
| DELETE | `/api/bot/sessions/:userId` | 刪除 Bot Session |

#### 3. 設計特點
- **可擴展性**: 新增狀態機時不需修改資料庫結構
- **容錯性**: API 失敗時不影響 Bot 正常運作
- **效能**: 使用記憶體快取 + SQLite 持久化雙層架構

---

## [1.1.1] - 2025-12-19

### ✨ 資料同步、匹配效率與標識強化

#### 1. 資料路徑與檔案讀取修復
**檔案**: `src/index.js` (L26)
- **修正**：`GUEST_ORDERS_PATH` 路徑補上 `data/` 前綴，修正為 `../../data/chat_logs/guest_orders.json`，確保能正確讀取 Bot 產出的訂單資料。

#### 2. OTA 訂單編號智能匹配
**檔案**: `src/index.js` (L47-51)
- **變更**：`matchGuestOrder` 函數新增 OTA ID 匹配邏輯。機器人收集時常使用外部訂單號（如 RMAG...），現在後端能自動關聯 PMS 內部 ID 與外部 OTA ID。

#### 3. LINE 用戶資料整合 (Display Name)
**檔案**: `src/index.js` (L26-44, L91-178)
- **新功能**：新增 `getUserProfiles()` 讀取 `user_profiles.json`。
- **邏輯優化**：`processBookings` 函數現在會根據 `line_user_id` 自動從 profiles 查找客人的 LINE 暱稱。
- **欄位優先級**：LINE 姓名顯示邏輯優化為 `SQLite > profiles > Bot-extracted > null`。

#### 4. 前端來源標識 (Phone Origin)
**檔案**: `src/index.js` (L149)
- **新欄位**：新增 `phone_from_bot` (Boolean) 欄位，用以標示電話號碼是否經由 Bot 驗證或提供，供前端 UI 變色參考。

---

## [1.1.0] - 2025-12-18

### ✨ 新功能：SQLite 擴充資料持久化與共享備註 API

#### 1. 資料庫層 (SQLite)
- **檔案**: `src/helpers/db.js`
- **實作**: 建立 `guest_supplements` 表，支援 `booking_id`, `confirmed_phone`, `arrival_time`, `staff_memo`, `ai_extracted_requests` 等欄位。

#### 2. API 端點擴充
- **檔案**: `src/index.js`
- **新增**: `PATCH /api/pms/supplements/:id` - 支援部分更新訂單擴充資料，並透過 WebSocket 廣播。
- **優化**: `async processBookings` - 讀取 PMS 資料時自動 Left Join SQLite 資料庫，合併最新的電話、時間與備註。

#### 3. 核心邏輯升級
- **檔案**: `src/index.js`
- **修改**: 將 `processBookings` 轉為非同步函數，並在 `today-checkin`, `tomorrow-checkin` 等路由中 awaiting。

## [1.0.1] - 2025-12-17

### ✨ 新功能：已 KEY 訂單自動匹配驗證

#### API 端點修改
**檔案**: `src/index.js`

**端點**: `PATCH /api/pms/same-day-bookings/:order_id/checkin` (L542-625)

#### 實作細節

1. **查詢臨時訂單** (L549-567)
   ```javascript
   const sameDayRes = await fetch('http://192.168.8.3:3000/api/bookings/same-day-list')
   const targetBooking = bookings.find(b => 
     b.item_id === order_id || b.order_id === order_id
   )
   ```

2. **查詢 PMS 今日入住名單** (L569-578)
   ```javascript
   const pmsRes = await fetch('http://192.168.8.3:3000/api/bookings/today-checkin')
   ```

3. **電話號碼匹配** (L580-598)
   - **匹配邏輯**: 電話號碼後 9 碼相同
   - **容錯**: 最少 8 碼即可匹配
   ```javascript
   const targetPhone = (targetBooking.phone || '').replace(/\D/g, '').slice(-9)
   const pmsPhone = (pms.contact_phone || '').replace(/\D/g, '').slice(-9)
   if (pmsPhone === targetPhone && targetPhone.length >= 8) {
     matched = true
   }
   ```

4. **狀態處理** (L600-625)
   - **匹配成功**: 呼叫 PMS API `/checkin` 端點，標記為 `checked_in`
   - **匹配失敗**: 呼叫 PMS API `/mismatch` 端點，返回錯誤訊息
   ```javascript
   return res.json({ 
     success: false, 
     mismatch: true,
     error: 'PMS 中找不到同電話的訂單，請確認 PMS 資料是否正確'
   })
   ```

### 🔗 整合更新
- **PMS API 整合**: 新增 `/mismatch` 端點呼叫
- **錯誤處理**: 統一回傳格式，包含 `mismatch` flag

### 📝 修改的文件
- `src/index.js` (L542-625) - Checkin API 重構

---

## [1.0.0] - 2025-12-10

### 初始版本
- Express.js 基礎架構
- 通知推送端點
- 服務狀態監控
- WebSocket 支援
