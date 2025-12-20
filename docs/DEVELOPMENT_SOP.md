# KTW Bot 開發標準作業程序 (Development SOP)

> 本文件整合了專案的核心價值觀與具體執行規範，為開發工作的最高指導原則。

---

> [!CAUTION]
> **⚠️ 強制性提醒 (MANDATORY)**
> 
> 在進行任何**新增、維護、修改**工作之前，必須：
> 1. ✅ **先完整閱讀本文件** (DEVELOPMENT_SOP.md)
> 2. ✅ **確認相關規範與原則**
> 3. ✅ **再開始規劃與實作**
> 
> **違反此原則的變更將被視為不符合專案標準。**

---

## 1. 核心理念與原則 (Core Principles)

### 1.1 核心價值
*   **專業紀錄**：專業並記錄筆記結果，同步上傳 Notion/GitHub。都需採繁體中文，如需用到英文需加上中文註解 (Chinese Annotation)，尊崇 DRY (Don't Repeat Yourself) 原則。
    - **全語境繁體中文**：從 AI 的內部思考 (`thought`)、工具調用參數 (`TaskName`, `TaskStatus`, `Summary`) 到最終輸出，**全面禁止使用英文或簡體中文**（除非是程式碼關鍵字、API 名稱或專有名詞）。**若因技術必要需使用英文詞彙，必須在後方括號補充繁體中文註解 (Chinese Annotation)**。
*   **簡潔至上**：恪守 KISS (Keep It Simple, Stupid) 原則，崇尚簡潔與可維護性，避免過度工程化與不必要的防禦性設計。
*   **深度分析**：立足於第一性原理 (First Principles Thinking) 剖析問題，並善用工具以提升效率。
*   **事實為本**：以事實為最高準則。若有任何誤解，懇請坦率扶正，助我精進。

### 1.2 開發與流程
*   **開發工作流程**：均採 **System + Function Calling** 的最佳自動化客服人員結構。
*   **漸進式開發**：通過多輪對話迭代，明確並實現需求。在著手任何設計或編碼工作前，必須完成前期調研並釐清所有疑點，需參考先前資料或筆記。
*   **結構化流程**：嚴格遵循「構思方案 → 提煉骨架 → 分解為具體任務」的作業順序。

### 1.3 System + Function Calling 架構原則 ⭐

> **核心理念**：收到客人對話後，讓 AI 判斷和確認需要用到哪些模組，採 AI + Function Calling 運行模組邏輯，AI 運用知識庫和模組邏輯進行問答。逐步強化邏輯，AI 就會一直成長。

**運作流程**：
```
客人訊息
    ↓
AI (Gemini) + System Prompt
    ↓
判斷意圖 → 決定調用哪個 Function
    ↓
┌─────────────────────────────────┐
│ Functions (工具/模組)           │
├─────────────────────────────────┤
│ check_today_availability()      │ ← 查詢房況
│ create_same_day_booking()       │ ← 建立預訂
│ check_order_status()            │ ← 查詢訂單
│ get_weather_forecast()          │ ← 天氣查詢
│ update_guest_info()             │ ← 更新客人資訊
│ ...                             │ ← 持續擴充
└─────────────────────────────────┘
    ↓
Function 回傳結果
    ↓
AI 結合知識庫生成自然回覆
```

**持續優化方式**：
1. **新增 Function**：增加新功能模組
2. **調整 System Prompt**：優化 AI 判斷邏輯
3. **累積知識庫**：豐富 FAQ 與業務知識
4. **分析對話日誌**：找出 AI 誤判案例並修正

**禁止事項**：
- ❌ 不使用**脫離 AI 理解**的純硬編碼狀態機（應該先透過 AI 判定意圖，再由狀態機接手流程）
- ❌ 不使用硬編碼正則表達式取代 AI 理解（僅能在 AI 失敗時作為輔助校驗）
- ❌ 不繞過 AI 指令直接強行跳轉模組（除非是系統級重置）

### 1.4 對話系統架構原則：模組化狀態機 (Modular FSM) ⭐

> **適用範圍**：本原則專用於 `LINEBOT` (bot.py) 等需要處理複雜、有狀態之對話流程的組件。
> 
> **核心理念**：結合「確定性的狀態機」以保證商務邏輯安全，並輔以「靈活的 AI 工具調用」提升服務溫度。

**主要組件**：
1.  **狀態機導向 (State-Machine Driven)**：使用 `ConversationStateMachine` 進行 Session 管理。這不是為了取代 AI，而是為了在 AI 判定意圖後，**強制確保商務流程的完整性**（如訂單確認必須經過電話校驗）。
2.  **處理器委派模式 (Handler Delegation Pattern)**：`bot.py` 主路由僅負責意圖分發。各功能塊（如 `OrderQueryHandler`, `VIPServiceHandler`）各自獨立管理其內部的任務邏輯。
3.  **工具調用模型 (Tool-Calling)**：這是 AI 的執行手腳。當狀態處於閒置 (`idle`) 時，由 AI 根據客人的自然語言自主決定調用哪些 tools（如 `update_guest_info`）。

**架構優勢**：
- **安全與穩健**：狀態機保證了關鍵欄位不遺漏、不幻覺。
- **靈活性**：非關鍵流程由 AI 代理處理，提升對話的自然度與應變能力。
- **可擴展性**：新增功能只需建立新的 Handler 並註冊至路由，不會汙染現有邏輯。
- **持久化支援**：結合 SQLite 實現長效 Session，中斷後可無縫銜接。

### 1.5 輸出規範
*   **測試驗證**：輸出前自己必須模擬真實測試，反覆確認。
*   **語言絕對要求**：**全程繁體中文**。這包含：
    1.  **內部思考 (Thought Phase / 思考階段)**：AI 在動手前的邏輯推演。
    2.  **工具參數 (Tool Arguments / 工具參數)**：如 `task_boundary` 的 `TaskName`、`TaskStatus` 等。
    3.  **所有文檔 (Artifacts / 產出文檔)**：`Implementation Plan` (實作計畫), `Task List` (任務清單), `Walkthrough` (成果演示)。
    - **補充規則**：若遇到無法避免的英文（如 API 名稱 `generate_content`），須以 `英文 (繁體中文註解)` 格式呈現。
*   **固定格式**：`Implementation Plan`, `Task List`

---

## 2. 文檔持續迭代細則 (Documentation SOP)

> ⚠️ **執行原則**：程式碼與文檔必須同步。任何功能變更若未反映在文檔中，則視為「未完成」。

### 2.1 執行時機

**一般文檔更新** (README, API 規格, Guide):
- **每次任務結束前** (在交付成果之前)
- 當修改了核心邏輯、API 介面或環境變數時

**CHANGELOG 更新** (版本記錄):
- 發布新版本時 (詳見 2.2 第 5 項)
- 重大功能變更、Bug 修復、破壞性變更時

### 2.2 自動檢查清單 (Auto-Checklist)
AI 代理在結束任務前，必須執行以下檢查：

1.  **目錄級 README**
    - 修改 `LINEBOT/` 程式碼 ➜ 更新 `LINEBOT/README.md`
    - 修改 `pms-api/` 程式碼 ➜ 更新 `pms-api/README.md`
    - **重點**：更新新功能說明、參數變更、依賴項。

2.  **API 規格文檔**
    - 變更 API 介面/格式 ➜ 更新 `pms-api/PMS-DATABASE-REFERENCE.md`。
    - 確保 `PMS-DATABASE-REFERENCE.md` 為資料庫結構的 **單一真實來源 (SSOT)**。

3.  **環境變數**
    - 新增 `.env` 變數 ➜ 同步更新 `.env.example`。

4.  **連結完整性**
    - 移動/重命名文件 ➜ 全域搜尋並修復所有斷裂的 Markdown 連結。

5.  **版本變更記錄 (CHANGELOG)** ⭐
    - **架構原則**：採用 **Monorepo 階層式變更日誌**,根目錄提供聚合摘要,各模組維護詳細記錄。
    - **執行時機**：
      - ✅ 發布新版本時 (最重要)
      - ✅ 新增功能時
      - ✅ 修復 Bug 時
      - ✅ 破壞性變更時 (Breaking Changes)
      - ✅ 重大優化時
      - **記憶法**：如果值得寫在 Git commit message,就值得寫在 CHANGELOG
    - **更新流程**：
      1. 先更新模組 CHANGELOG (如 `LINEBOT/CHANGELOG.md`)
      2. 再更新根目錄 `CHANGELOG.md` (簡潔摘要 + 連結)
    - **遵循原則**：SSOT (單一真實來源) + DRY (不重複)
    - **架構說明**：
      ```
      /CHANGELOG.md              ← 統整所有模組 (簡潔格式)
      /LINEBOT/CHANGELOG.md      ← LINE Bot 詳細記錄
      /KTW-admin-web/CHANGELOG.md ← Admin Dashboard 詳細記錄
      /KTW-backend/CHANGELOG.md  ← Backend API 詳細記錄
      /pms-api/CHANGELOG.md      ← PMS API 詳細記錄
      ```

### 2.3 CHANGELOG 編寫規範 ⭐

#### 必要元素
每個版本記錄必須包含：

1. **版本號與日期**
   ```markdown
   ## [1.2.0] - 2025-12-17
   ```
   
   **版本號編排規則** (Semantic Versioning):
   - **格式**: `主版本.次版本.修訂版本` (MAJOR.MINOR.PATCH)
   - **遞增規則**: 由前一版本的**最小號版本 +1** 開始編排
   
   **範例**:
   ```
   v1.1.6 (前一版本)
     ↓
   v1.1.7 (Bug 修復) ← 修訂版本 +1
     ↓
   v1.2.0 (新功能)   ← 次版本 +1, 修訂版本歸零
     ↓
   v2.0.0 (破壞性變更) ← 主版本 +1, 次版本與修訂版本歸零
   ```
   
   **何時遞增**:
   - **主版本 (X.0.0)**: 重大架構變更、不兼容的 API 修改
   - **次版本 (1.X.0)**: 新增功能、向後兼容
   - **修訂版本 (1.1.X)**: Bug 修復、小改進

2. **變更分類**
   - ✨ 新功能 (New Features)
   - 🐛 Bug 修復 (Bug Fixes)
   - ⚡ 性能優化 (Performance)
   - 🎨 UI/UX 改進 (UI/UX)
   - 📝 文檔更新 (Documentation)
   - 🔧 配置變更 (Configuration)

3. **詳細資訊** (關鍵！)
   - **檔案路徑**: 完整的相對路徑 (如 `src/App.vue`)
   - **行號範圍**: 修改的程式碼位置 (如 L197-220)
   - **修改內容**: 具體做了什麼改動
   - **修改原因**: 為什麼要這樣改
   - **影響範圍**: 影響了哪些功能

#### 範例格式

```markdown
### ✨ 新功能：已 KEY 訂單自動匹配驗證

#### 核心邏輯 (Frontend)
**檔案**: `src/App.vue`

1. **狀態計算與排序** (L197-220)
   - 新增 `hasMismatch` 狀態檢查
   - 更新 `groupStatus` 優先順序：`mismatch > pending > checked_in > cancelled`
   - 實作排序邏輯：KEY 錯訂單置頂，已 KEY 訂單過濾隱藏

2. **API 整合** (L261-282)
   - 修改 `markAsKeyed()` 函數，處理 Backend 返回的 `mismatch` 狀態
   - 延長 API timeout 至 10 秒（因需查詢 PMS）
   - 新增錯誤處理：匹配失敗時刷新列表顯示 KEY 錯狀態

### 🐛 Bug 修復

1. **多房型床型錯誤**
   - **檔案**: `bot.py` (L1171)
   - **問題**: 所有房型共用同一個 `bed_type`
   - **修復**: 解析床型字串，為每個房型分配正確床型
   - **影響**: 修復多房型預訂時床型資訊錯誤的問題

### 📝 修改的文件
- `src/App.vue` (L197-220, L261-282) - 狀態邏輯、API 整合
- `src/style.css` (L1670-1706) - 新增 mismatch 相關樣式
```

#### 禁止事項
- ❌ 只寫「修復 Bug」而不說明具體問題
- ❌ 只寫「優化性能」而不說明優化了什麼
- ❌ 不寫檔案路徑和行號
- ❌ 不說明修改原因

### 2.4 README 編寫規範

#### 必要章節
每個模組的 `README.md` 必須包含：

1. **模組概述**
   - 一句話說明模組用途
   - 核心功能列表 (用 ✅ 標記已完成功能)

2. **技術架構**
   - 技術棧 (語言、框架、主要依賴)
   - 系統架構圖 (用 ASCII 或 Mermaid)

3. **檔案結構**
   - 目錄樹狀圖
   - 關鍵檔案說明

4. **快速開始**
   - 環境需求
   - 安裝步驟
   - 啟動指令

5. **核心功能說明**
   - 每個主要功能的詳細說明
   - 使用範例

6. **開發指南**
   - 如何修改配置
   - 如何新增功能
   - 相關文檔連結

7. **故障排除**
   - 常見問題與解決方案

8. **版本資訊**
   - 當前版本號
   - 最後更新日期
   - CHANGELOG 連結

#### 範例格式

```markdown
# 模組名稱

> 一句話說明模組用途

---

## 📋 模組概述

### 核心功能
- ✅ 功能 1
- ✅ 功能 2
- ⏸️ 功能 3 (開發中)

---

## 🏗️ 技術架構

### 技術棧
- **語言**: Python 3.9+
- **框架**: Flask

### 系統架構
\`\`\`
用戶 → API → 資料庫
\`\`\`

---

## 📁 檔案結構

\`\`\`
module/
├── README.md
├── CHANGELOG.md
└── src/
\`\`\`

---

## 🚀 快速開始

### 環境需求
- Python 3.9+

### 安裝
\`\`\`bash
pip install -r requirements.txt
\`\`\`

---

## 📝 版本資訊

- **當前版本**: v1.2.0
- **最後更新**: 2025-12-17
- **維護者**: KTW Hotel IT Team

詳細變更記錄請參閱 [CHANGELOG.md](./CHANGELOG.md)
```

#### 更新時機
- 新增功能時 → 更新「核心功能」章節
- 修改架構時 → 更新「技術架構」章節
- 新增環境變數時 → 更新「快速開始」章節
- 修改版本時 → 更新「版本資訊」章節

---

## 3. 程式修改前置標準流程 (Pre-Coding SOP)

> ⚠️ **執行原則**：在修改任何程式碼之前，必須嚴格執行以下三步驟。禁止直接寫 Code。

### 步驟 1：歷史回顧與文件查閱 (Context Retrieval)
*   **強制查閱**：必須先閱讀相關的 `README.md`、`GUIDE.md` 或架構文檔。
*   **確認現況**：理解現有程式碼的設計意圖，避免破壞既有邏輯 (Regression)。

### 步驟 2：前瞻後顧與最佳模式分析 (Impact Analysis)
*   **最佳模式**：思考「這是業界的最佳實踐 (Best Practice) 嗎？」
*   **前瞻**：這個修改對未來擴充有幫助嗎？會不會造成技術債？
*   **後顧**：這個修改會不會影響舊功能？是否與現有架構衝突？

### 步驟 3：方案研擬與利弊分析 (Scenario Planning)
在動手前，必須向使用者提出 **3 種解決方案**，並進行利弊分析：

| 方案 | 說明 | 優點 (Pros) | 缺點 (Cons) | 建議程度 |
|:---:|:---|:-----------|:-----------|:-------:|
| **A** | (方案名稱) | ... | ... | ⭐⭐⭐ |
| **B** | (方案名稱) | ... | ... | ⭐⭐ |
| **C** | (方案名稱) | ... | ... | ⭐ |

*   **討論與決策**：與使用者討論並達成共識後，才可進入實作階段 (Coding)。

---

## 4. API 設計思維 (API Design Philosophy)

在面對複雜的舊系統時，API 不應只是資料庫的 CRUD 介面，而是**業務能力的封裝**。

### 4.1 核心原則

1.  **意圖導向 (Intent-Based)**
    *   ❌ **Don't**: `GET /api/guest_mn?id_cod=...` (暴露底層資料表)
    *   ✅ **Do**: `GET /api/guests/search?identity=...` (封裝業務動作)
    *   **理由**：解耦前後端。底層資料來源可能從 Oracle 換成 PostgreSQL，但 API 介面應保持穩定。

2.  **防腐層 (Anti-Corruption Layer, ACL)**
    *   **原則**：絕不讓舊系統的髒命名 (Legacy Naming) 汙染新系統。
    *   **實作**：在 API 層 (Node.js) 進行轉換。
        *   `IKEY` ➜ `bookingId`
        *   `GUEST_MN` ➜ `GuestProfile`
        *   `CI_DAT` ➜ `checkInDate`

3.  **讀取優化 (Read-Optimized)**
    *   **現況**：舊系統過度正規化，導致查詢緩慢。
    *   **策略**：針對高頻查詢（如「今日入住名單」），在 API 層做聚合 (Aggregation)，一次回傳完整 JSON，減少前端往返次數。

---

## 5. 舊資料庫探索技巧 (Legacy DB Exploration)

Oracle PMS 是一個黑盒子，探索需講求方法。

### 5.1 探索 SOP

1.  **Trace > Guess (追蹤勝於猜測)**
    *   優先查看 Application Log 或開啟 SQL Trace，觀察系統在執行特定動作（如 check-in）時觸發了哪些 SQL。這比看欄位名稱猜測準確得多。

2.  **Data-Driven Inference (數據推斷)**
    *   不確定欄位用途時，使用 `SELECT DISTINCT` 查看實際存儲的值。
        ```sql
        -- 用數據說話：看 GUEST_STA 到底有哪些狀態
        SELECT DISTINCT GUEST_STA, COUNT(*) FROM GUEST_MN GROUP BY GUEST_STA;
        ```

3.  **建立映射文檔 (Mapping Document)**
    *   持續維護 `pms-api/PMS-DATABASE-REFERENCE.md`，這是團隊最重要的資產。

4.  **協作分析與討論 (Collaborative Analysis)** ⭐
    *   **原則**：查到任何不明確的欄位或數據時，**務必提交給使用者分析**。
    *   **理由**：使用者熟悉舊系統的前端邏輯（Frontend Logic），能從欄位值中發現工程師看不出的業務線索（例如：某個 Flag 代表的特定業務流程）。
    *   **行動**：在 Task List 或討論中列出 `[欄位名]: [範例值]`，邀請使用者共同判讀。

### 5.2 PMS 欄位表格維護規範 ⭐

> [!IMPORTANT]
> **核心原則**：`pms-api/PMS-DATABASE-REFERENCE.md` 是資料庫結構的 **單一真實來源 (SSOT)**。
> 
> 此文件的準確性直接影響未來自建資料庫的正確性，必須嚴格維護。

**維護流程**：

1.  **發現新欄位或代碼**
    - 透過 SQL 查詢 (`SELECT DISTINCT`) 探索欄位的可能值
    - 記錄原始欄位名、實際數據、推測用途

2.  **交叉比對驗證**
    - 與 PMS 系統的實際行為進行比對
    - 確保欄位描述與觀察到的數據一致

3.  **提交使用者確認** ⭐
    - **強制規定**：任何新發現的欄位或代碼說明，必須先與使用者確認後才能寫入文檔
    - **理由**：使用者了解業務邏輯，能識別 AI 或工程師可能誤解的專業術語
    - **格式**：提供表格形式的對照說明，方便使用者快速審閱

4.  **更新文檔並記錄**
    - 確認後更新 `PMS-DATABASE-REFERENCE.md`
    - 在 CHANGELOG 中記錄欄位定義的變更

**範例：瑕疵房 vs 維修房**

| 類型 | 判斷條件 | 說明 | 可售？ |
|:-----|:---------|:-----|:------:|
| 瑕疵房 | `OOS_STA = Y` 且 `ROOM_STA = V` | 有小問題但可賣 | ✅ |
| 維修房 | `ROOM_STA = R` | 正在維修 | ❌ |

> **此定義經 2025-12-21 使用者確認**

---

## 6. 資料庫遷移策略 (Migration Strategy)

### 6.1 戰略：絞殺榕模式 (Strangler Fig Pattern)

絕對禁止採用 Big Bang (一次性切換) 模式。應採用**雙軌並行**策略，逐步替換。

### 6.2 執行階段 (Phases)

#### Phase 1: 旁路模式 (Sidecar) - **目前階段**
*   **狀態**：Oracle (Master) ➜ PostgreSQL (Read-Only Slave/Cache)
*   **機制**：單向同步。寫一個排程器 (Scheduler) 每 5 分鐘從 Oracle 撈取異動資料，寫入 PostgreSQL。
*   **用途**：LINE Bot、Admin Dashboard 讀取 PostgreSQL，速度快且不影響舊系統效能。寫入操作仍回到 Oracle。

#### Phase 2: 增量寫入 (Incremental Write)
*   **狀態**：新功能資料直接寫入 PostgreSQL。
*   **案例**：LINE 加好友紀錄、Wifi 授權紀錄、AI 對話日誌。這些是舊系統沒有的功能，直接在新架構落地。

#### Phase 3: 影子寫入 (Shadow Write)
*   **狀態**：嘗試接管寫入。
*   **機制**：當用戶在 Bot 訂房時，API 同時寫入 PostgreSQL 和 Oracle（透過原廠介面或模擬操作）。比對兩邊結果是否一致，確保邏輯正確。

#### Phase 4: 切換 (Cutover)
*   **狀態**：PostgreSQL 升級為主庫 (Master)。
*   **條件**：Oracle 降級為僅供查詢的歷史存檔庫 (Archive)。

---

## 7. 結論 (Summary)

*   **API 層**：做翻譯官，不要做傳聲筒。把 `IKEY` 翻譯成 `bookingId` 再給前端。
*   **DB 層**：先求共存，再求取代。從「讀取優化」開始，建立信心後再處理「寫入」。

---

*文件最後更新：2025-12-20*
