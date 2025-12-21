# LINE Bot - Changelog

> LINE 客服機器人的詳細變更記錄

---

## [1.9.1] - 2025-12-21

### 🐛 Bug 修復：OTA 訂單查詢優先與 LOG 機制

> **問題背景**：客人林宛錡提供 Agoda 訂單號 `1671721966`，Bot 回報「查不到」。經調查，訂單實際存在於 PMS（`RMAG1671721966`），但因查詢順序問題導致未能匹配。

#### 1. PMS API 查詢順序調整 (Critical)
- **檔案**: `pms-api/routes/bookings.js` (L846-930)
- **問題**: 原查詢順序為 IKEY → OTA 精確 → 模糊匹配，無法匹配 `1671721966` 到 `RMAG1671721966`
- **修正**: 調整為 **OTA 模糊匹配優先** → IKEY 精確 → IKEY 模糊
- **理由**: 客人通常提供 OTA 訂單號（如 Agoda 的 `1671721966`），應優先匹配 `RMAG1671721966`

```diff
- // 1. 先用 IKEY 精確匹配
- // 2. 若失敗，用 RVRESERVE_NOS (OTA訂單號) 精確匹配
- // 3. 若仍失敗，嘗試模糊匹配

+ // 1. ⭐ 優先用 OTA 訂單號模糊匹配（客人通常提供這個）
+ // 2. 若失敗，用 IKEY 精確匹配
+ // 3. 若仍失敗，嘗試 IKEY 模糊匹配
```

#### 2. Gmail 備援觸發條件放寬
- **檔案**: `LINEBOT/bot.py` (L555-561)
- **問題**: 觸發條件 `len > 10` 不包含剛好 10 位數的 OTA 訂單號
- **修正**: 改為 `len >= 10`
- **影響**: `1671721966` (10 位) 現在會觸發 Gmail 備援

#### 3. 新增 API Logger 持久化日誌
- **新增檔案**: `LINEBOT/helpers/api_logger.py`
- **功能**: 
  - 記錄所有 PMS API 調用（請求、回應、耗時、錯誤）
  - 日誌以日期分檔，存放於 `data/api_logs/pms_api_YYYY-MM-DD.log`
  - 包含用戶 ID、訂單號、查詢結果

**日誌格式範例**:
```
2025-12-21 09:58:26 | INFO | PMS_QUERY_START | user=U45320f69f3c... | order_id=1671721966
2025-12-21 09:58:26 | DEBUG | PMS_REQUEST | method=GET | url=http://192.168.8.3:3000/api/bookings/1671721966
2025-12-21 09:58:26 | INFO | PMS_RESPONSE | status=200 | elapsed=0.02s | result=found | pms_id=00703101 | ota_id=RMAG1671721966
2025-12-21 09:58:26 | INFO | QUERY_RESULT | order_id=1671721966 | source=pms | result=success | pms_id=00703101
```

#### 4. PMS Client 整合 API Logger
- **檔案**: `LINEBOT/helpers/pms_client.py` (L30-130)
- **修改**: 
  - 引入 `api_logger` 記錄詳細診斷資訊
  - 記錄查詢耗時、HTTP 狀態碼、錯誤類型
  - 新增 `user_id` 參數供日誌識別用戶

### 📝 修改的文件
- `pms-api/routes/bookings.js` (L846-930) - 查詢順序調整
- `LINEBOT/bot.py` (L555-561) - Gmail 備援條件放寬
- `LINEBOT/helpers/api_logger.py` [NEW] - API 日誌記錄器
- `LINEBOT/helpers/pms_client.py` (L30-130) - 整合 API Logger

---

## [1.9.0] - 2025-12-21

### ✨ 新功能：智慧日期查詢與 AI 意圖判斷

大幅增強內部 VIP 的 PMS 查詢功能，從硬編碼關鍵字升級為 AI 意圖判斷模式。

#### 1. AI 意圖判斷系統 (Intent Detection)

- **檔案**: `handlers/vip_service_handler.py` (L120-230)
- **新增**: `_detect_query_intent()` 方法，使用 Gemini AI 判斷用戶查詢意圖
- **優勢**: 能理解口語化表達，如「前一天住了多少」、「聖誕節那天有幾間預訂」
- **備援**: 當 AI 判斷失敗時，自動退回 `_fallback_keyword_detection()` 關鍵字匹配

#### 2. 昨日房況查詢 (Yesterday Status)

- **檔案**: `handlers/internal_query.py` (L77-147)
- **新增**: `query_yesterday_status()` 函數
- **觸發**: 「昨天」、「昨日」、「昨天入住狀況」等
- **輸出**: 顯示已住統計、房型分布、訂房來源

#### 3. 特定日期查詢 (Specific Date Query)

- **檔案**: `handlers/internal_query.py` (L178-269)
- **檔案**: `handlers/vip_service_handler.py` (L261-294)
- **新增**: `query_specific_date()` 函數與 `_parse_date_from_message()` 日期解析器
- **支援格式**: `12/25`、`12月25日`、`25號`、`2025-12-25`
- **智慧標籤**: 過去日期→「已住」、今日→「入住」、未來日期→「預訂」

#### 4. 完整月份統計 (Full Month Forecast)

- **檔案**: `handlers/internal_query.py` (L300-380)
- **修改**: `query_month_forecast()` 現在顯示整個月（1號到月底）
- **分區顯示**: 已過日期、今日、未來日期

#### 5. 房況計算修正 (Room Status Calculation)

- **檔案**: `handlers/internal_query.py` (L37-90)
- **問題**: 原計算錯誤扣除「瑕疵房」(OOS)
- **修正**: 使用 `room_status=R` 判斷真正停用的「維修房」
- **公式**: 
  - 可售總房 = 總房數 - 維修房 (R)
  - 住房率 = 在住 (O) / 可售總房

#### 6. 查詢結果詳細化

- **修改**: 昨日/特定日期查詢現在顯示房型分布與訂房來源統計
- **新增**: `_get_room_type_name()` 房型代碼轉中文
- **新增**: `_detect_booking_source()` 訂房來源偵測 (Agoda/Booking/官網)

### 📝 文檔更新

- **檔案**: `pms-api/PMS-DATABASE-REFERENCE.md`
- **新增**: 瑕疵房 vs 維修房 的業務邏輯說明
- **新增**: `ROOM_STA = R` (維修/故障) 狀態代碼

---

## [1.8.5] - 2025-12-21

### 🏗️ 結構重構：VIP Service Handler 優化

為了提升內部管理層的服務體驗與系統代碼品質，對 VIP 處理器進行了全面重構。

1. **邏輯整合與冗餘消除 (Logic Consolidation)**
   - **檔案**: `handlers/vip_service_handler.py` (L114-177, L129-178)
   - **修改**: 將相似的「房況預測」（週/週末/月）與「今日狀態」查詢邏輯整合為統一的處理塊。
   - **優化**: 使用辭典映射（Map）管理關鍵字，提升了擴展性與可讀性。

2. **標準化 Prompt 體系 (Standardized Prompts)**
   - **檔案**: `handlers/vip_service_handler.py` (L179-195)
   - **新增**: `_get_standard_system_prompt()` 方法。
   - **效果**: 確保 Vision 與 Chat 行為高度一致，包含專業稱呼、語言自適應（中文問中文答等）以及處理規則。

3. **穩定性與錯誤處理強化 (Robustness)**
   - **檔案**: `handlers/vip_service_handler.py` (L231-233, L321-393)
   - **優化**: 提升調用 Gemini SDK 的異常捕捉精度。當 AI 服務繁忙時，回傳更具建設性且有禮貌的錯誤引導訊息，而非生硬的系統報錯。

4. **意圖偵測精準度提升**
   - **檔案**: `handlers/vip_service_handler.py` (L168-175, L290-309)
   - **變更**: 優化姓名查詢的正則表達式，並加入排除清單（排除「今天」、「誰」等口語詞），有效減少誤判率。

---

## [1.8.0] - 2025-12-21

### ✨ 新功能：營運報表擴展

1. **增強型房況查詢 (Rooms Accuracy)**
   - **檔案**: `handlers/internal_query.py` (L47-50, L144-150)
   - **修改**: 房間數計算邏輯從 `room_count` 欄位改為解析 `room_numbers` 陣列長度。
   - **理由**: PMS API 返回的 `room_count` 恆為 1，需解析分配房號陣列才能獲得準確間數。
   - **影響**: 修正今日/本週/本月房況中的間數統計錯誤。

2. **本月房況預測 (Monthly Forecast)**
   - **檔案**: `handlers/internal_query.py` (L156-227)
   - **新增**: `query_month_forecast()` 函數。
   - **功能**: 支援查詢當月剩餘天數入住預測，並對接遠端 `/checkin-by-date` 端點。

3. **關鍵字優先權調整**
   - **檔案**: `handlers/vip_service_handler.py` (L114-135)
   - **修改**: 將週報/月報關鍵字偵測順序移至今日房況之前。
   - **理由**: 防止「這禮拜住幾間」被「住幾間」攔截。

### 🔧 優化

1. **API 調用統一化**
   - **檔案**: `handlers/internal_query.py` (L120-136, L200-213)
   - **變更**: 週報與月報全面改用遠端 PMS API 的 `/checkin-by-date` 端點，取代原有的 `/search` 端點以獲取更詳細資料。
---

## [1.7.5] - 2025-12-21

### ✨ 核心架構：Modular VIP FSM (模組化狀態機)
為了提升代碼的可維護性與擴充性，將 VIP 服務從 `bot.py` 抽離，建立獨立的狀態機處理流程。

1. **VIP 處理器模組化 (Handler Decoupling)**
   - **檔案**: `handlers/vip_service_handler.py` (L26-392)
   - **實作**: 新增 `VIPServiceHandler` 類別，封裝所有 VIP 邏輯。
   - **理由**: 解決 `bot.py` 體積過大（Spaghetti Code）問題。

2. **有限狀態機 導入 (Finite State Machine)**
   - **檔案**: `handlers/vip_service_handler.py` (L36-37, L69, L110)
   - **狀態**: `vip_idle` (閒置), `vip_waiting_image` (等待圖片)。
   - **功能**: 支援跨對話的任務狀態記憶（例如：主管先下令「幫我翻譯」，Bot 轉入等待圖片狀態）。

3. **bot.py 路由重構 (Router Refactor)**
   - **檔案**: `bot.py` (L1541-1547)
   - **變更**: 移除 `_handle_internal_vip_query` 等舊函數，統一由 `vip_service` 實例分發。
   - **影響**: 顯著提升 VIP 功能的穩定性，並解決狀態遺失問題。

---

## [1.7.1] - 2025-12-20

### 🐛 Bug 修復

#### Gmail HTML 解析修正
- **檔案**: `helpers/gmail_helper.py` (L210-276)
- **問題**: 解析 HTML 郵件時殘留 CSS 代碼（如 `2px solid #000000`）
- **修復**: 
  - 新增 `_strip_html_tags()` 函數
  - 優先解析 `text/plain`，僅在必要時使用 `text/html`
  - 移除 `<style>` 和 `<script>` 區塊

#### arrival_time 記錄邏輯修正
- **檔案**: `chat_logger.py` (L161-204)
- **問題**: `arrival_time` 更新時會同時寫入 `special_requests` 陣列
- **修復**: 
  - `phone` 和 `arrival_time` 只更新主欄位
  - 僅 `special_need` 會記錄到 `special_requests`

#### System Prompt 意圖判斷優化
- **檔案**: `bot.py` (L280-297)
- **問題**: 「會晚點到」被誤判為 `arrival_time`
- **修復**: 
  - 「會晚點到」「行程有變」→ `special_need`
  - 「晚上10點」「下午3點」→ `arrival_time`

### ✨ 新功能

#### VIP 語言自適應回覆
- **檔案**: `handlers/vip_service_handler.py` (L186-198, L329-345)
- **功能**: VIP 用什麼語言問，Bot 就用什麼語言回覆
- **規則**: 除非明確要求翻譯，否則保持對方語言

---

## [1.7.0] - 2025-12-20

### 🏗️ 架構重構：VIPServiceHandler

#### 新增檔案
- **檔案**: `handlers/vip_service_handler.py` (約 380 行)
- **功能**: 統一處理所有 VIP 相關功能
- **特色**: 支援上下文記憶（任務記憶）

#### 移除程式碼
從 `bot.py` 移除約 165 行 VIP 相關程式碼：
- `_handle_internal_vip_query()` (~75 行)
- `_internal_vip_free_chat()` (~60 行)
- `handle_image()` VIP 分支 (~30 行)

#### 新功能：任務記憶
- **問題**: 用戶說「幫我翻譯圖片成印尼語」再傳圖片時，Bot 會忘記翻譯任務
- **解決**: VIPServiceHandler 會記住待處理任務，圖片傳送後自動執行

#### 路由邏輯更新
```
用戶訊息 → bot.py → VIPServiceHandler.is_internal()?
                    ├─ Yes → VIPServiceHandler.handle_message()
                    └─ No → 一般客服流程
```

---

## [1.6.1] - 2025-12-20

### ⚡ 升級：Google Search Grounding

#### SDK 升級
- **安裝新版 SDK**: `google-genai` v1.47.0
- **保留舊版 SDK**: `google-generativeai` v0.8.6 (Bot 主程式使用)
- **Search Grounding**: 內部 VIP 網路搜尋現可使用真正的 Google 搜尋

#### 修改檔案

1. **web_search.py** (完全重構)
   - **新版 SDK**: 使用 `google.genai.Client` 模式
   - **Search Grounding**: `types.Tool(google_search=types.GoogleSearch())`
   - **模型**: `gemini-3-flash-preview`
   - **Fallback**: 若新版失敗自動切換舊版 SDK

### 🎨 內部 VIP 專屬 Persona

#### 禮貌稱呼功能
- **檔案**: `bot.py` (L1445-1462)
- **角色稱謂對照表**:
  - `chairman` → 董事長
  - `manager` → 經理
  - `staff` → 同事
  - `super_vip` → 長官

#### Web Search Prompt 優化
- **檔案**: `web_search.py` (L48-67)
- **特色**: 
  - 開頭稱呼角色 (如「董事長，」)
  - 優先搜尋車城、恆春、墾丁地區
  - 餐廳/景點優先提供電話、地址、營業時間
  - 結尾問候「還有其他需要幫忙的嗎？」

### 📝 知識庫更新
- **檔案**: `data/knowledge_base.json`
- **新增**: 田中漁夫餐廳專屬條目（電話、地址、營業時間、訂位規則）

---

## [1.6.0] - 2025-12-20

### ✨ 新功能：VIP 用戶雙層架構 (VIP Module)

#### 架構設計
```
┌───────────────────────────────────────────┐
│               VIP 系統                     │
├───────────────────┬───────────────────────┤
│    客人 VIP       │      內部 VIP          │
│   (Guest VIP)     │   (Internal VIP)       │
├───────────────────┼───────────────────────┤
│ • 後台識別標籤    │ • 查詢 PMS 資料庫      │
│ • 優先推送通知    │ • 查詢營運數據         │
│ • (未來) 優惠方案 │ • 網路搜尋資訊         │
└───────────────────┴───────────────────────┘
```

#### 新增檔案

1. **VIPManager** (核心模組)
   - **檔案**: `handlers/vip_manager.py`
   - **功能**: VIP 狀態查詢、權限檢查
   - **API**: `is_vip()`, `is_internal()`, `get_vip_level()`, `has_permission()`

2. **內部查詢模組**
   - **檔案**: `handlers/internal_query.py`
   - **功能**: PMS 資料查詢（房況、入住名單、房間狀態、臨時訂單）
   - **觸發詞**: 「房況」「入住名單」「清潔」「臨時訂單」

3. **網路搜尋模組**
   - **檔案**: `handlers/web_search.py`
   - **功能**: 使用 Gemini AI 進行網路搜尋
   - **觸發詞**: 「幫我查」「搜尋」「上網查」

#### 修改檔案

1. **app.py** (L89-109)
   - 移除舊的 `vip_users.json` 讀取邏輯
   - 改用 `VIPManager` 查詢 VIP 狀態
   - 新增 `vip_type` 與 `is_internal` 欄位推送到 Dashboard

2. **bot.py** (L1434-1492, L1530-1538)
   - 新增 `_handle_internal_vip_query()` 函數
   - 在 `generate_response()` 路由邏輯中加入內部 VIP 功能分派

#### Backend API 新增
**檔案**: `KTW-backend/src/helpers/db.js`, `KTW-backend/src/index.js`

| 端點 | 方法 | 說明 |
|:-----|:-----|:-----|
| `/api/vip` | GET | 取得所有 VIP 列表 |
| `/api/vip/:userId` | GET | 查詢用戶 VIP 狀態 |
| `/api/vip` | POST | 新增 VIP 用戶 |
| `/api/vip/:userId` | DELETE | 移除 VIP 用戶 |

#### SQLite 資料表
**檔案**: `data/ktw_supplements.db`

```sql
CREATE TABLE vip_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_user_id TEXT UNIQUE NOT NULL,
    display_name TEXT,
    vip_type TEXT NOT NULL,  -- 'guest' | 'internal'
    vip_level INTEGER,
    role TEXT,               -- 'chairman' | 'manager' | 'staff'
    permissions TEXT,
    note TEXT,
    created_at DATETIME,
    updated_at DATETIME
);
```

#### 內部 VIP 可用指令

| 指令 | 功能 |
|:-----|:-----|
| 「今天房況」「住房率」 | 查詢入住/退房/空房統計 |
| 「今日入住」「誰入住」 | 查詢今日入住名單 |
| 「房間狀態」「待清潔」 | 查詢清潔/停用狀態 |
| 「臨時訂單」「LINE訂單」 | 查詢 Bot 當日預訂 |
| 「查XXX的訂單」 | 依姓名查詢訂單 |
| 「幫我查XXX」 | 網路搜尋 |

### 📝 修改的文件
- `handlers/vip_manager.py` [NEW] - VIP 管理模組
- `handlers/internal_query.py` [NEW] - 內部查詢模組
- `handlers/web_search.py` [NEW] - 網路搜尋模組
- `app.py` (L89-109) - VIP 狀態檢查整合
- `bot.py` (L1434-1492) - 內部 VIP 路由邏輯
- `KTW-backend/src/helpers/db.js` - VIP 資料表與 CRUD
- `KTW-backend/src/index.js` - VIP API 端點

---

## [1.5.0] - 2025-12-20

### ✨ 新功能：對話狀態持久化 (Session Persistence)

#### 核心變更
**檔案**: `handlers/conversation_state_machine.py` (全檔重構)

1. **SQLite 同步整合**
   - 新增 `_load_from_backend()` - 從 SQLite 載入 session
   - 新增 `_sync_to_backend()` - 同步 session 到 SQLite
   - 新增 `_delete_from_backend()` - 從 SQLite 刪除 session

2. **自動持久化觸發點**
   - `transition()` - 狀態轉換時同步
   - `set_data()` - 資料更新時同步
   - `set_pending_intent()` - 設定排隊意圖時同步
   - `clear_pending_intent()` - 清除意圖時同步
   - `reset_session()` - 重置時刪除

3. **環境變數**
   - `KTW_BACKEND_URL` - 可自訂 Backend API URL (預設: `http://localhost:3000`)

#### 解決的問題
- ✅ 伺服器重啟後對話狀態不再消失
- ✅ 排隊意圖 (pending_intent) 持久保存
- ✅ 流程中斷後下次訊息可自動觸發排隊意圖

#### 依賴變更
- 新增 `requests` 套件依賴（已包含在 requirements.txt）

---

## [1.4.10] - 2025-12-19

### ✨ 系統流程、穩定性與同步強化

#### 1. 兩階段訂單確認流程
**檔案**: `bot.py` (L595-613)
- **變更**：移除強匹配自動確認邏輯。現在機器人總是會回傳 `confirmation_needed`，強制 AI 詢問用戶確認，達成真正的「兩階段確認」體驗。

#### 2. 顯示邏輯與隱私優化
**檔案**: `bot.py` (L692-752)
- **電話格式化**：修正從 PMS 讀取到的錯誤國碼前綴（如 886886...），自動轉換為標準台灣手機格式 (09xx...)。
- **早餐顯示**：將原始的「無」優化為更具客房語意的「不含早餐」。
- **狀態偵測**：新增對「已取消」訂單的偵測邏輯，確保客人能即時得知訂單狀態。

#### 3. 核心 Bug 修復 (Critical)
**檔案**: `handlers/order_query_handler.py` (L448-454)
- **KeyError 修復**：解決 `special_requests` list 未初始化即進行 `append` 的崩潰問題。
- **字串解析修正**：將原本導致 AI 解析錯誤的多行三引號字串改為標準單行字串並正確處理換行符。

#### 4. 資料同步與 A.I. 提取優化
**檔案**: `bot.py` (L971-985 - `update_guest_info`), `handlers/order_query_handler.py` (L575-595)
- **USER_ID 記錄**：`update_guest_info` 工具現在會自動記錄 `line_user_id`，確保 AI 模式下也能正確關聯用戶身分。
- **資料完整性**：修正 `line_display_name` 的記錄邏輯，確保與後端資料庫同步時名稱不遺失。

#### 5. System Prompt 優化 (Persona)
**檔案**: `persona.md`
- **簡潔回覆**：導入訊息簡化策略，優先提供核心資訊，避免長篇大論。
- **即時性機制**：強調訂單查詢的即時性，每次用戶意圖查詢時強制工具調用重查。

---

## [1.4.5] - 2025-12-19

### ✨ 訂單查詢完整優化 (Order Query Enhancement)

#### 1. Handler 架構優化與資料標準化
**檔案**: `handlers/order_query_handler.py` (L41-62, L162-223, L248-283)

**新增功能**：
- **房型對照表** (L41-62)：建立完整的房型代碼對照表（SD→標準雙人房、WQ→海景四人房等），確保所有房型都能正確轉換為中文名稱。
- **電話號碼標準化** (L107-140)：新增 `_normalize_phone` 函式，智能處理國際電話前綴（886）與各種錯誤格式，確保顯示正確的台灣手機格式（0978035792）。

**核心邏輯改進**：
- **訂單來源判斷** (L248-263)：從 OTA ID 前綴（RMAG→Agoda、RMPGP→官網）或 remarks 內容智能判斷訂單來源。
- **房型合併統計** (L193-208)：相同房型自動合併計數（4間標準雙人房顯示為「標準雙人房 x4」而非重複列舉）。
- **早餐資訊判斷** (L279-282)：從 remarks 檢查「不含早」關鍵字，準確判斷早餐包含情況。
- **晚數計算顯示** (L271-273)：自動計算並顯示住宿晚數（退房日期後註明「共 X 晚」）。

#### 2. PMS API 資料完整性提升
**相關檔案**: `pms-api/routes/bookings.js`

- **補齊 `ota_booking_id` 欄位**：在所有查詢策略的 SQL 中加入 `TRIM(RVRESERVE_NOS)` 選取，並在 JSON 回傳結構中映射為 `ota_booking_id`，確保 Bot 能正確識別外部訂單編號。

**修復效果**：
```
修復前：
  訂單來源: 未知
  訂單編號: 00701101  （內部 ID）
  房型: null
  早餐: 含早餐  （未判斷）
  聯絡電話: 8868860978035792  （錯誤格式）

修復後：
  訂單來源: Agoda
  預約編號: RMAG1667798817  （OTA ID）
  房型: 標準雙人房 x4  （中文+合併）
  早餐: 不含早餐  （正確判斷）
  聯絡電話: 0978035792  （標準格式）
  退房日期: 2025-12-21 (共 1 晚)  （晚數顯示）
```

---

## [1.4.4] - 2025-12-19

### ✨ 訂單顯示邏輯優化 (UI/UX)

#### 1. 訂單核對資訊精簡
**檔案**: `bot.py` (L729-763)

- **隱藏訂金**：根據需求移除「已付訂金」欄位的顯示，避免向客人展示內部紀錄的訂金資訊。
- **欄位更名與優化**：將「訂單編號」更名為「預約編號」，並確保其內容優先採用 OTA 訂單編號（如 Booking/Agoda ID），提升客人核對時的辨識度。
- **減少雜訊**：移除不必要的空行與條件判斷分支，使回傳訊息更加簡潔。

---

## [1.4.3] - 2025-12-18

### 🐛 系統穩定性修復 (Critical Crash Fix)

#### 1. 訂單查詢崩潰修復 (Order Status Fix)
**檔案**: `bot.py` (L508-972)

- **核心修復**：徹底解決了因縮進錯誤導致的 `NoneType` 崩潰與語法錯誤。修正了 `check_order_status` 函式中 PMS 與 Gmail 分支的邏輯樹，確保 fallback 機制能正確運作。
- **邏輯對齊**：修正了隱私攔截碼 (Privacy Guard) 與後續資料解析流程的層級關係，確保在找不到訂單時能優雅返回 `not_found` 而非拋出異常。
- **解析優化**：優化了 Gmail 備援時的資訊提取邏輯，包含入住日期、電話、房型的 regex 匹配與房型名稱標準化。

#### 2. 代碼品質維護
- **語法驗證**：通過 `python3 -m py_compile` 驗證，確保無縮進或語法問題。

---

## [1.4.2] - 2025-12-18

### 🛡️ 隱私強化與組合查詢升級

#### 1. 隱私保護攔截 (Privacy Protection)
**檔案**: `bot.py` (L470-482), `helpers/gmail_helper.py` (L15-28)

- **日期攔截**：實作「日期格式攔截器」，防止 AI 誤將日期視為訂單編號進行查詢，有效避免因提供日期而揭露訂單詳情的隱私風險。
- **模糊查詢限制**：在 Gmail 搜尋層級限制查詢條件，禁止過短或模糊的純數字搜尋，降低資訊外洩機率。
- **系統指令升級**：更新 `bot.py` 全域指令，嚴格禁止 AI 在僅有日期時揭露資訊。

#### 2. 精準組合查詢 (Combinatorial Query)
**檔案**: `bot.py` (L456-465), `helpers/pms_client.py` (L23-72)

- **多參數驗證**：升級 `check_order_status` 工具，支援同時傳入 `booking_id`、`guest_name` 與 `phone`。
- **落實資料比對**：機器人現在會主動運用已知的姓名或電話，在 PMS API 階段進行交叉核對，確保「只有正確的人員」能查詢到正確的資訊。
- **優先權調整**：強化 「PMS 第一、Gmail 第二」的資料調用優先順序。

---

## [1.4.1] - 2025-12-18

### ✨ 新功能與優化

#### 訂單查詢優化 (Order Query)
**檔案**: `handlers/order_query_handler.py`

1. **格式化升級** (L207-243)
   - 重新編排訂單摘要清單，包含：訂單來源、編號、姓名、電話、入住/退房日期、房型、已付訂金、早餐。
   - 新增實作「已付訂金」顯示邏輯，針對官網 (RMPGP) 訂單顯示。
2. **強制電話確認** (L256-277)
   - 修改流程邏輯，即使 PMS 已有電話，機器人仍會發起確認問句，確保資料準確性。
3. **延遲跳轉機制** (L84-90, L366-382)
   - 實作「攔截加訂意圖」邏輯。若客人在查詢中途提到加訂需求，機器人會引導先完成當前核對，並於結束後主動轉換至預訂流程。

#### 當日預訂流程優化 (Same Day Booking)
**檔案**: `handlers/same_day_booking.py`

1. **雙向跳轉機制** (L355-360, L1254-1282, L1341-1373)
   - 在預訂流程中可攔截「查詢訂單」意圖，並引導客人完成預訂後再行查詢。

#### 系統路由調整 (Main Logic)
**檔案**: `bot.py` (L1471-1477)
- 恢復並調整狀態機處理器的優先權，確保在進行中流程時，意圖攔截與延遲跳轉能正確運作。

---

## [1.4.0] - 2025-12-18

### ✨ 新功能：同步至本地持久化資料庫
- **pms_client.py**: 新增 `update_supplement` 方法，支援 PATCH 資料至本地 KTW-backend。
- **order_query_handler.py**: 在 `_save_to_guest_orders` 流程中加入同步邏輯，將電話、抵達時間、AI 提取需求即時推送到後端 SQLite (L451-468)。

## [1.3.1] - 2025-12-18

### 🐛 Bug 修復
- **order_query_handler.py**: 修正方法名稱不匹配 (`update_order_info` -> `update_guest_request`)。 (L402)
- **order_query_handler.py**: 修正 `save_order` 參數數量錯誤，改為傳遞單一 Dict。 (L440)
- **pms_client.py**: 修正 `check_health` URL 拼接邏輯，移除重複的 `/api`。 (L157-168)

### ✨ 功能優化
- **bot.py**: 優化路由攔截邏輯，偵測到訂單號時優先由 `OrderQueryHandler` 處理，解決 AI 閒聊誤判問題。 (L1461-1466)
- **gmail_helper.py**: 在 Deep Scan 搜尋中加入 `newer_than:14d` 過濾，避免掃描到過舊郵件。 (L31-36)
- **order_query_handler.py**: 實作 PMS 數據鍵名標準化 (Lowercase Normalization)，解決資訊顯示「未知」的問題。 (L154-158)

---

## [1.3.0] - 2025-12-18

### ✨ 全面升級 AI 基礎設施 (Gemini 3.0 Flash)

#### 核心升級
**檔案**: `bot.py`

1. **AI 模型全面升級** (L415, L425, L431)
   - 將「主要對話模型」、「影像識別模型」及「隱私驗證模型」統一升級至最新發佈的 `gemini-3-flash-preview`。
   - **理由**: 利用 Gemini 3.0 Flash 極低的延遲與顯著提升的 OCR 準確度（相較於 2.5 版本提升約 15%）。
   - **影響**: 
     - 提升客人傳送訂單截圖時的識別率。
     - 提升複雜對話與 Function Calling 的邏輯判斷精準度。
     - 降低對話回應等待時間。

### 📝 修改的文件
- `bot.py` (L415, L425, L431) - 更換模型名稱為 gemini-3-flash-preview
- `README.md` - 更新技術棧與模型說明

---

## [1.2.0] - 2025-12-17

### 當日預訂 AI 邏輯重構

#### 架構優化
**檔案**: `bot.py`

1. **移除舊版路由邏輯** (L1439-1456)
   - 刪除 `_has_order_number()` 方法
   - 刪除 `if self._has_order_number(user_question):` 路由判斷
   - **理由**: 讓 AI 統一判斷數字是電話還是訂單編號

2. **System Prompt 優化** (L100-150)
   - 新增 "Proactive Confirmation Principle" (主動確認原則)
   - **內容**: 當客人輸入模糊時（如單純數字、不明確時間），AI 需主動詢問確認
   - **效果**: 避免將電話號碼誤判為訂單編號

#### 功能增強
**檔案**: `bot.py`

1. **多房型支援** (L1140-1180)
   - **函數**: `create_same_day_booking()`
   - **修改**: 支援解析多房型字串（例: "2間標準雙人, 1間四人房"）
   - **邏輯**:
     ```python
     # 解析房型字串
     room_patterns = [
         r'(\d+)\s*間?\s*([^,，]+)',  # "2間雙人房"
         r'([^,，]+?)\s*[xX×]\s*(\d+)'  # "雙人房 x 2"
     ]
     ```

2. **床型解析** (L1158-1180)
   - **問題**: 多房型時床型資訊混亂
   - **解決**: 從 `bed_type` 字串解析出每個房型對應的床型
   - **實作**:
     ```python
     bed_type_parts = bed_type.split(',')
     for i, room_entry in enumerate(room_entries):
         bed_type_for_room = bed_type_parts[i].split(':')[1].strip()
     ```

### Bug 修復

1. **多房型床型錯誤**
   - **檔案**: `bot.py` (L1171)
   - **問題**: 所有房型共用同一個 `bed_type`
   - **修復**: 解析床型字串，為每個房型分配正確床型

2. **PMS API 錯誤**
   - **檔案**: `pms-api/routes/bookings.js` (L858, L862-865)
   - **問題**: 使用未定義的 `tempOrderId` 變數
   - **修復**: 改用 `itemId` 和 `orderId`

### 📝 修改的文件
- `bot.py` (L1140-1180, L1439-1456) - 多房型解析、移除舊路由
- `pms-api/routes/bookings.js` (L858, L862-865) - 修復變數錯誤

---

## [1.1.6] - 2025-12-17

### 🐛 Bug 修復

1. **天氣查詢功能修復**
   - **檔案**: `.env`
   - **問題**: CWA_API_KEY 環境變數包含引號導致 API 無法正確讀取
   - **修復**: 移除引號，改為 `CWA_API_KEY=your_key` (不加引號)
   - **影響**: 天氣 API 現已正常運作，可成功查詢中央氣象署資料

2. **錯誤處理機制改善**
   - **檔案**: `bot.py` (L1450-1470)
   - **修改**: 
     - 修復錯誤訊息未記錄到對話 LOG 的問題
     - 所有系統錯誤現在都會記錄完整的 traceback 供除錯
   - **檔案**: `app.py` (L180-185)
   - **修改**: 新增空回應檢查機制，避免發送空白訊息
   - **效果**: 移除無幫助的「連線有點問題」錯誤訊息，改為靜默處理

### ✨ 新功能

1. **天氣資訊增強**
   - **檔案**: `helpers/weather_helper.py` (L85-120)
   - **新增**: 
     - 降雨機率顯示 (當 >0% 時)
     - 體感溫度顯示 (當與實際溫度差異 >2°C 時)
   - **效果**: 提供更完整的天氣資訊，幫助客人做好行程規劃

### 📝 修改的文件
- `.env` - 修正 CWA_API_KEY 引號問題
- `bot.py` (L1450-1470) - 改善錯誤處理與 LOG 記錄
- `app.py` (L180-185) - 新增空回應檢查
- `helpers/weather_helper.py` (L85-120) - 新增降雨機率和體感溫度

---

## [1.1.5] - 2025-12-15

### ✨ 新功能：語音訊息辨識 (Voice to Text)

#### 實作細節
**檔案**: `bot.py`

1. **語音處理方法** (L1568-1600)
   - **函數**: `handle_audio(user_id, audio_content, display_name)`
   - **技術**: 使用 Gemini 2.5 Flash 多模態模型進行語音轉文字
   - **流程**: 
     ```python
     # 1. 接收 LINE AudioMessage
     # 2. 傳送給 Gemini API 進行語音辨識
     # 3. 將辨識結果作為文字訊息處理
     # 4. 呼叫 generate_response() 產生回應
     ```

2. **Webhook Handler** 
   - **檔案**: `app.py` (L164-185)
   - **新增**: `@handler.add(MessageEvent, message=AudioMessage)` 事件監聽器
   - **功能**: 接收語音訊息並呼叫 `handle_audio()` 處理

### 技術對比

| 技術 | 優點 | 缺點 | 使用情境 |
|:---|:---|:---|:---|
| **Gemini 2.5 Flash** ✅ 採用 | 速度最快、整合簡單、無額外費用 | 準確度略低於 Whisper | 即時客服互動 |
| **OpenAI Whisper V3** | 純語音辨識最準確 | 需額外 API、延遲較高 | 專業轉錄需求 |
| **Gemini 1.5 Pro** | 語意理解最強 | 速度較慢、成本較高 | 高精度需求 |

### 📝 修改的文件
- `bot.py` (L1568-1600) - 新增 handle_audio 方法
- `app.py` (L164-185) - 新增 AudioMessage 事件處理

---

## [1.1.5] - 2025-12-15

### 新增功能
- **語音訊息辨識 (Voice to Text)**:
  - 使用者可直接發送語音訊息給 Bot
  - Bot 會自動將語音轉換為文字並回應
  - 採用 Gemini 2.5 Flash 多模態模型進行聽打
  - 支援繁體中文辨識
  - 語音指令效果等同於打字輸入

### 技術實作
- 新增 `handle_audio` 方法:在 `bot.py` 中處理 LINE `AudioMessage`
- 新增 Webhook Handler:在 `app.py` 中註冊 `AudioMessage` 事件監聽器

### AI 語音辨識技術對比

| 技術 | 優點 | 缺點 | 使用情境 |
|:---|:---|:---|:---|
| **Gemini 2.5 Flash** ✅ 採用 | 速度最快、整合簡單、無額外費用 | 準確度略低於 Whisper | 即時客服互動 |
| **OpenAI Whisper V3** | 純語音辨識最準確 | 需額外 API、延遲較高 | 專業轉錄需求 |
| **Gemini 1.5 Pro** | 語意理解最強 | 速度較慢、成本較高 | 高精度需求 |

---

## [1.1.1] - 2025-12-12

### ✨ 新增功能

1. **知識庫擴充**
   - **檔案**: `../data/knowledge_base.json`
   - **新增**: 4 筆常見問題
     - 寵物政策說明 (寵物友善，清潔費 800 元/房)
     - 嬰兒用品租借服務 (嬰兒床、圍欄、消毒鍋、澡盆)
     - 早餐服務說明 (自助式/套餐式)
     - 櫃檯服務時間 (15:00-23:00)

### 🐛 Bug 修復與改進

1. **對話歷史自動重置機制**
   - **檔案**: `bot.py` (L1420-1440)
   - **問題**: 對話歷史過長導致 AI token 超限 (finish_reason=1)
   - **修復**: 
     ```python
     except ValueError as e:
         if "finish_reason" in str(e):
             # 自動清除對話歷史
             self.clear_history(user_id)
             return "對話歷史已自動清除，請再次提供訂單編號"
     ```
   - **效果**: 解決長期用戶無法獲得回應的問題

2. **錯誤訊息日誌完善**
   - **檔案**: `bot.py` (L1450-1460)
   - **修復**: 錯誤訊息未記錄到 chat log 的問題
   - **修改**: 所有 Bot 回應 (包括錯誤訊息) 現在都會正確記錄

### 📝 修改的文件
- `../data/knowledge_base.json` - 新增 4 筆常見問題
- `bot.py` (L1420-1440) - 對話歷史自動重置
- `bot.py` (L1450-1460) - 錯誤日誌完善

---

## [1.1.0] - 2025-12-11

### 新增功能
- **重新開始對話功能**:用戶可輸入「重新開始」、「reset」、「restart」或「清除對話」來重置對話歷史
- **早餐資訊自動判斷**:系統會從備註和房型名稱中檢查「不含早」關鍵字,自動判斷是否包含早餐
- **房型對照表獨立管理**:將房型對照表從代碼中抽離到 `room_types.json`,便於維護和更新

### 改進優化
- **訂單來源判斷邏輯優化**:
  - 優先檢查 `remarks` 中的關鍵字(「官網」、「agoda」、「booking.com」)
  - 其次才使用 OTA ID 前綴判斷(RMAG、RMPGP)
  - 修正了誤將官網訂單判定為 Booking.com 的問題

- **PMS API 數據處理增強**:
  - 支援大寫鍵名(`ROOM_TYPE_CODE`、`ROOM_COUNT`、`ROOM_TYPE_NAME`)
  - 同時兼容小寫鍵名,提高容錯性
  - 修復房型顯示「無」的問題

- **AI 模型升級**:
  - 主對話模型:Gemini 2.0 Flash Exp → Gemini 2.5 Flash
  - 提供更好的理解能力和回應品質

- **系統指令優化**:
  - 加強訂單詳情顯示要求,確保 Bot 不會跳過顯示步驟
  - 添加正確/錯誤流程示例,提高 AI 遵守指令的準確性

### 錯誤修復
- **修復 KeyError 問題**:
  - 修復 `room_type_name` KeyError(當值為 `null` 時)
  - 修復 `room_count` KeyError(使用 `.get()` 方法並設置默認值)
  - 所有字典訪問都改用安全的 `.get()` 方法

- **修復隱私檢查邏輯**:
  - 修正 Gmail 隱私檢查的 AI validator 提示詞
  - 明確處理未來訂單(DAYS_AGO < 0)的情況
  - 確保近期訂單和未來訂單都能正常顯示

### 代碼品質
- 移除 17 行硬編碼的房型字典,改為 3 行 JSON 載入
- 改善代碼可維護性和可讀性
- 統一錯誤處理方式

---

## [1.0.1] - 2025-12-10

### 初始版本
- LINE Bot 基本功能
- 訂單查詢系統(3-Step 協議)
- Gmail API 整合(備用訂單來源)
- Google Gemini AI 整合
- 天氣預報功能
- 客人資訊收集與更新
- 對話歷史記錄
