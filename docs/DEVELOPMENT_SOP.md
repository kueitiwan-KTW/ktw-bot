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
*   **簡潔至上**：恪守 KISS (Keep It Simple, Stupid) 原則，崇尚簡潔與可維護性，避免過度工程化與不必要的防禦性設計。
*   **深度分析**：立足於第一性原理 (First Principles Thinking) 剖析問題，並善用工具以提升效率。
*   **事實為本**：以事實為最高準則。若有任何誤解，懇請坦率扶正，助我精進。

### 1.2 開發與流程
*   **開發工作流程**：均採 System + Function 的最佳自動化客服人員結構。
*   **漸進式開發**：通過多輪對話迭代，明確並實現需求。在著手任何設計或編碼工作前，必須完成前期調研並釐清所有疑點，需參考先前資料或筆記。
*   **結構化流程**：嚴格遵循「構思方案 → 提煉骨架 → 分解為具體任務」的作業順序。

### 1.3 輸出規範
*   **測試驗證**：輸出前自己必須模擬真實測試，反覆確認。
*   **語言要求**：所有回覆、思考過程及任務清單，均須使用繁體中文。
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

*文件最後更新：2025-12-17*
