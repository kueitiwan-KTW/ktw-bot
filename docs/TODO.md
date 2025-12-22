# KTW Bot 待辦功能 (TODO)

> 記錄待實作的功能需求

---

## 📋 待辦項目

### 【高優先】本月統計顯示「使用中房間」

**需求描述**：
- 目前「本月入住狀況」只顯示「當日新入住」的筆數/間數
- 但如果有客人續住（住多晚），第二天起就不會被計入
- 應該顯示「**當日使用中的房間數**」（入住 + 續住）

**計算公式**：
```
使用中房間 = 入住日期 ≤ 當日 且 退房日期 > 當日
```

**範例**：
- 訂單 00703801：12/27 入住，12/29 退房（住 2 晚）
- 12/27：新入住 1 間 ✅
- 12/28：**續住 1 間**（目前顯示 0，應顯示 1）
- 12/29：退房

**影響範圍**：
- `LINEBOT/handlers/internal_query.py` - `query_month_forecast()`
- 可能需要 PMS API 新端點或修改查詢邏輯

**提出日期**：2025-12-21

---

### 【中優先】Gemini SDK 升級

**需求描述**：
- 目前使用舊版 SDK：`google-generativeai` v0.8.6
- 官方已宣布棄用 (deprecated)，建議切換至 `google.genai`

**升級影響**：
- 需重構 `bot.py`、`web_search.py`、`vip_service_handler.py` 中的 import
- 新 SDK 使用 `Client()` 模式，API 呼叫方式不同
- 可解鎖新功能：`thinking_level` 參數控制

**影響範圍**：
- `LINEBOT/bot.py` - 主要 AI 調用
- `LINEBOT/handlers/web_search.py` - 網路搜尋
- `LINEBOT/handlers/vip_service_handler.py` - VIP 服務

**參考文檔**：
- https://ai.google.dev/gemini-api/docs/gemini-3

**提出日期**：2025-12-21

---

### 【中優先】Bot 模組化重構

**需求描述**：
- ~~`bot.py` 目前 1821 行，太肥~~ ✅ 已完成
- `same_day_booking.py` 目前 1724 行，仍需精簡
- 目標：單一檔案控制在 500-800 行

**已完成項目**（2025-12-22）：
- ✅ `bot.py` 從 1821 行減至 817 行（-55%）
- ✅ 抽離 System Prompt 至 `prompts/system_prompt.py`
- ✅ `check_order_status` 改為 Wrapper，邏輯移至 Handler
- ✅ `create_same_day_booking` 改為 Wrapper，邏輯移至 Handler

**待完成項目**：
- [ ] 精簡 `same_day_booking.py`（1724 行 → 目標 800 行）
- [ ] 建立 `helpers/intent_router.py` - 統一意圖路由
- [ ] 移除重複的 `ROOM_TYPE_MAP`

**提出日期**：2025-12-21
**更新日期**：2025-12-22

---

### 【低優先】統一暫存資料庫架構

**需求描述**：
- 當日預訂儲存在 `pms-api/data/same_day_bookings.json`（每日清除）
- 訂單補充資料儲存在 `KTW-backend/data/ktw_supplements.db`（長期保存）
- 兩者分散不同位置，維護不便

**整合方案**：
將當日預訂從 JSON 遷移到 SQLite，統一使用 `ktw_supplements.db`：

```sql
-- 新增 Table
CREATE TABLE same_day_bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,           -- WI12221722
    pms_id TEXT,                      -- 入住後關聯的 PMS 訂單號
    guest_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    room_type_code TEXT,
    room_type_name TEXT,
    room_count INTEGER DEFAULT 1,
    bed_type TEXT,
    arrival_time TEXT,
    status TEXT DEFAULT 'pending',    -- pending/checked_in/cancelled
    line_user_id TEXT,
    line_display_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME               -- 每日 3 點
);
```

**優點**：
1. 統一資料位置
2. 可用 SQL 查詢關聯分析
3. 當日預訂入住後可與 `guest_supplements` 關聯

**影響範圍**：
- `pms-api/routes/bookings.js` - POST/GET same-day 端點
- `KTW-backend/src/index.js` - 新增 API
- `LINEBOT/helpers/pms_client.py` - 調整 API 調用
- 需新增每日 3 點清除的排程任務

**提出日期**：2025-12-22

---

### 【高優先】漸進式暫存功能測試

**已完成項目**（2025-12-22）：
- ✅ PMS-API 支援 `incomplete` 狀態跳過必填驗證
- ✅ PMS-API 支援用 `line_user_id` 核對，避免重複訂單
- ✅ Bot 在 `check_today_availability` 時就暫存 LINE 資訊
- ✅ Admin-Web 顯示 `guest_name` 和 `line_display_name`

**待測試項目**：
- [ ] 測試完整當日預訂流程（今天超過 20:00，明天再測）
- [ ] 確認訂單不會重複（用 LINE ID 核對）
- [ ] 確認中途離開時 Admin-Web 有顯示 incomplete 訂單

**待開發項目**：
- [ ] AI 中途收集資訊時更新暫存（新增 `update_booking_info` 工具）
- [ ] 客人回來時查詢恢復進度（已有 API，Bot 端未接入）

**相關檔案**：
- `pms-api/routes/bookings.js` - POST same-day 端點
- `LINEBOT/bot.py` - check_today_availability
- `LINEBOT/handlers/same_day_booking.py` - create_booking_for_ai
- `LINEBOT/helpers/pms_client.py` - get_user_incomplete_booking

**提出日期**：2025-12-22

---

### 【長期】商業化 PMS 規劃

**目標**：將 KTW Bot + Admin-Web 發展成商業化 PMS 系統

**產品架構**：
```
┌─────────────────────────────────────────────────┐
│           公開網站層                              │
├─────────────────────────────────────────────────┤
│ 🌐 形象官網 (Next.js)   📱 LINE Bot (Flask)       │
│ (品牌展示/訂房入口)      (客服/當日訂房)            │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│           管理層                                 │
├─────────────────────────────────────────────────┤
│ 🖥️ Admin-Web / PMS (Vue + TypeScript)           │
│ (房況/訂單/入住/報表/權限)                         │
└─────────────────────────────────────────────────┘
                       │
┌─────────────────────────────────────────────────┐
│           資料層                                 │
├─────────────────────────────────────────────────┤
│ 🗄️ PostgreSQL (主資料庫)                         │
│ 📦 Redis (快取)                                  │
└─────────────────────────────────────────────────┘
```

**待開發項目**：

1. **帳號權限系統**
   - [ ] JWT Token + RBAC（Role-Based Access Control）
   - [ ] 角色：超級管理員、櫃檯、房務、會計
   - [ ] 登入/登出/密碼重設

2. **技術升級**
   - [ ] Admin-Web 改用 TypeScript
   - [ ] 資料庫遷移到 PostgreSQL
   - [ ] 加入 Auth 中介層

3. **部署架構**
   - [ ] Admin-Web → Vercel（靜態托管）
   - [ ] LINE Bot → Cloud Run
   - [ ] PMS API → Cloud Run
   - [ ] 資料庫 → Cloud SQL

4. **形象官網**
   - [ ] 技術選型：Next.js（SSR 對 SEO 好）
   - [ ] 功能：房型介紹、線上訂房、相簿、位置
   - [ ] 訂房整合：接官網訂房引擎 or 自建

5. **Bot 設定 UI（SaaS 自助設定）**
   - [ ] 基本資訊：飯店名稱、地址、電話、Logo
   - [ ] 房型設定：新增/編輯/刪除房型、價格、床型
   - [ ] 知識庫編輯器：FAQ 問答管理
   - [ ] AI 人格設定：口吻、暱稱、表情符號風格
   - [ ] 訂房規則：當日截止時間、取消政策
   - [ ] LINE 設定：Channel Token、Webhook URL

**提出日期**：2025-12-22

---

*最後更新：2025-12-22*
