# KTW 系統轉型架構指引 (API & Migration Strategy)

> 本文件旨在定義從舊版 Oracle PMS 轉型至現代化架構的戰略思維與執行原則。

---

## 1. API 設計思維 (API Design Philosophy)

在面對複雜的舊系統時，API 不應只是資料庫的 CRUD 介面，而是**業務能力的封裝**。

### 1.1 核心原則 (Core Principles)

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

## 2. 舊資料庫探索技巧 (Legacy DB Exploration)

Oracle PMS 是一個黑盒子，探索需講求方法。

### 2.1 探索 SOP

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

## 3. 資料庫遷移策略 (Migration Strategy)

### 3.1 戰略：絞殺榕模式 (Strangler Fig Pattern)

絕對禁止採用 Big Bang (一次性切換) 模式。應採用**雙軌並行**策略，逐步替換。

### 3.2 執行階段 (Phases)

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

### 4. 結論 (Summary)

*   **API 層**：做翻譯官，不要做傳聲筒。把 `IKEY` 翻譯成 `bookingId` 再給前端。
*   **DB 層**：先求共存，再求取代。從「讀取優化」開始，建立信心後再處理「寫入」。

---

*文件建立日期：2025-12-17*
