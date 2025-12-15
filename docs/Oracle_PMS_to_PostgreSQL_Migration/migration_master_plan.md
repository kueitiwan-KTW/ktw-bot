# Oracle PMS → PostgreSQL 資料庫遷移計畫

## 1. 專案背景與目標

本計畫旨在指導將現有的 **Oracle Database (`GDWUUKT` Schema)** 遷移至開源的 **PostgreSQL** 資料庫。此遷移將降低授權成本，並利用 PostgreSQL 的現代化特性與豐富的開源生態系統 (如 PostGIS, JSONB 等) 來增強系統的靈活性。

## 2. 遷移策略選擇 (比較與建議)

在開始技術實施前，需選擇合適的遷移策略。

| 策略模式 | 說明 | 優點 | 缺點 | **建議情境** |
|:---|:---|:---|:---|:---|
| **Big Bang (一次性切換)** | 系統停機，一次性將資料全部匯出並匯入新庫，完成後切換應用程式指向。 | • 架構簡單，不需要資料同步機制<br>• 測試範圍明確 | • **停機時間長** (視資料量而定)<br>• 風險高，失敗需全量回滾 | 資料量小 (<50GB)，且允許數小時停機維護的系統。 |
| **Phased (分階段遷移)** | 按模組 (如訂單、會員) 分批遷移，新舊資料庫並存一段時間。 | • 風險分散<br>• 可逐步驗證 | • **極度複雜**：需處理跨庫關聯 (Join)、分散式交易與雙向同步 | 系統過於龐大且無法停機的超大型企業系統。**不建議本專案使用**。 |
| **Parallel Run (並行運行)** | 舊系統與新系統同時運行，雙寫資料，驗證新系統無誤後切換。 | • 風險最低<br>• 可隨時切回舊系統 | • **開發成本高**：需修改 App 支援雙寫<br>• 資料一致性維護困難 | 金融級核心系統，對數據準確性要求極高者。 |

✅ **本專案建議策略：改良版 Big Bang**
由於飯店 PMS 系統通常有夜間稽核或維護窗口，建議採用 **"預先同步 + 短暫停機切換"** 的方式：
1. 先進行**全量遷移** (Full Load) 到 PostgreSQL。
2. 設定 **CDC (Change Data Capture)** 工具持續同步 Oracle 的增量資料。
3. 在切換日 (Cutover Day) 停止 Oracle 寫入，等待最後一筆資料同步完成 (約數分鐘)。
4. 應用程式切換至 PostgreSQL。

---

## 3. 技術選型與工具比較

| 工具 | 用途 | 優點 | 缺點 | **評語** |
|:---|:---|:---|:---|:---|
| **ora2pg** | Schema 與資料遷移 | • 免費開源，Perl 編寫<br>• **Schema 轉換能力強** (自動轉 PL/SQL 為 PL/pgSQL)<br>• 報告詳細 | • 設定檔參數繁多<br>• 單執行緒效能較慢 (可開多核) | **強烈推薦** 用於 Schema 轉換評估與初步資料遷移。 |
| **AWS SCT + DMS** | Schema 與資料遷移 | • GUI 介面好操作<br>• 適合遷移上雲 (RDS/Aurora) | • 需依賴 AWS 環境<br>• 複雜 Stored Procedures 轉換率有限 | 若目標是 AWS RDS 可考慮。 |
| **Oracle GoldenGate** | 即時資料同步 | • 官方工具，穩定性極高<br>• 支援異質資料庫 | • **授權費用昂貴**<br>• 設定複雜 | 預算充足且需要零停機遷移時使用。 |
| **Debezium (Kafka)** | 即時資料同步 (CDC) | • 開源，基於 Kafka Connect<br>• 準即時同步 | • 架構複雜 (需維護 Kafka/Zookeeper)<br>• 運維成本高 | 若團隊熟悉 Kafka 可採用。 |

✅ **本專案工具建議：**
- **Schema 轉換**：使用 `ora2pg` (最成熟的開源方案)。
- **資料遷移**：
    - 全量：`ora2pg` 或 `COPY` 指令。
    - 增量 (Optional)：若停機視窗夠長，可直接全量遷移；若需縮短停機時間，可考慮手寫腳本根據 `UPDATE_TIME` 同步，或使用 `Debezium`。

---

## 4. 詳細實施步驟 (Implementation Guide)

### 階段一：評估與環境建置 (Assessment & Setup)

1.  **安裝 ora2pg**：
    ```bash
    # 在 遷移伺服器 (Linux 建議) 上安裝
    yum install ora2pg
    ```
2.  **產生評估報告**：
    使用 ora2pg 分析 Oracle Schema，它會估算遷移難度指數 (1-100) 與預估工時。
    ```bash
    ora2pg -t SHOW_REPORT -c ora2pg.conf > migration_report.html
    ```
3.  **建置 PostgreSQL 環境**：
    - 安裝 PostgreSQL 16+ (建議最新版)。
    - **參數優化 (postgresql.conf)**：針對 Oracle 使用習慣調整。
        - Standard Conforming Strings: `off` (若舊程式有大量 `\` 跳脫字元)。
        - DateStyle: `ISO, YMD` (確認與 Oracle 日期格式相容性)。

### 階段二：結構遷移 (Schema Migration)

此階段最為關鍵，需將 Oracle 的物件轉換為 PG 相容語法。

1.  **資料型態對映 (Mapping)**：
    | Oracle | PostgreSQL | 注意事項 |
    |:---|:---|:---|
    | `VARCHAR2(n)` | `VARCHAR(n)` / `TEXT` | PG 的 TEXT 效能極佳，無長度限制。 |
    | `NUMBER(n,0)` | `INTEGER` / `BIGINT` | 避免全用 `NUMERIC`，整數用 INT 效能較好。 |
    | `NUMBER(n,m)` | `NUMERIC(n,m)` | 用於金額等精確小數。 |
    | `DATE` | `TIMESTAMP(0)` | Oracle DATE 含時間，PG DATE 不含。**必須轉 TIMESTAMP**。 |
    | `CLOB` | `TEXT` | - |
    | `BLOB` | `BYTEA` | - |
    | `SYSDATE` | `CURRENT_TIMESTAMP` | - |

2.  **物件轉換執行**：
    使用 ora2pg 分批匯出 SQL 腳本：
    - `Tables` (資料表定義)
    - `Constraints` (Primary/Foreign Keys) - **建議資料匯入後再開啟以加速**。
    - `Indexes` (索引) - **建議資料匯入後再建立**。
    - `Views` (視圖)
    - `Procedures/Functions` (預存程序) - **最困難部分，需人工介入修正**。
    - `Sequences` (序列)
    
### 階段三：全量資料遷移 (Full Data Migration)

**目標：** 確保 Oracle 資料庫中的**每一筆資料** (包含所有歷史訂單、封存紀錄、系統設定) 均完整無誤地轉移至 PostgreSQL。

1.  **停用 Foreign Keys & Triggers**：
    在 PG 端暫時停用 FK 和 Trigger，大幅提升寫入速度。
    ```sql
    SET session_replication_role = 'replica';
    ```
2.  **執行全量匯入 (Full Import)**：
    - **方法 A (推薦)**：使用 `ora2pg` 的 `COPY` 模式。它會自動遍歷 Oracle 所有表格，將資料全數匯出並匯入 PG。
    - **確保歷史資料**：確認 Oracle export script 沒有設 `WHERE` 條件或是日期過濾，確保 10 年以上的歷史資料 (History Tables) 也被包含在內。
3.  **重置序列 (Sequences)**：
    資料匯入後，必須將 PG 的 Sequence 更新為 Oracle 對應欄位的最大值 (Max ID)，否則新增資料會報 PK 重複錯誤。
    ```sql
    SELECT setval('seq_name', (SELECT MAX(id) FROM table_name));
    ```
4.  **啟用 Foreign Keys & Triggers**：
    ```sql
    SET session_replication_role = 'origin';
    ```
5.  **建立索引 (Create Indexes)**：
    資料全進去後再建索引，效能會比一邊 insert 一邊建快很多。

### 階段四：應用程式改造 (Application Refactoring)

Node.js (`pms-api`) 需要做以下修改：

1.  **Driver 更換**：
    - 移除 `oracledb`
    - 安裝 `pg` (node-postgres)
2.  **SQL 語法修正**：
    - **Bind Variables**：Oracle 使用 `:name` 或 `:1`，PG 使用 `$1`, `$2`。
    - **Dual Table**：PG 不強制 `FROM DUAL` (雖然支援，但建議移除)。
    - **String Concat**：Oracle `||` (PG 支援，但注意 `NULL` 行為)。
    - **Date Functions**：
        - Oracle: `TO_CHAR(date, 'YYYY-MM-DD')`
        - PG: `TO_CHAR(date, 'YYYY-MM-DD')` (相容，但格式字串略有不同，如 `HH24`)。
        - Oracle: `TRUNC(SYSDATE)` -> PG: `CURRENT_DATE`。
3.  **Transaction 處理**：
    - 確保 `BEGIN`, `COMMIT`, `ROLLBACK` 機制在 PG Driver 中的正確實作。
    - Auto-commit 行為確認。

### 階段五：全量數據驗證測試 (Full Data Verification)

**目標：** 在切換前證明 PostgreSQL 的數據與 Oracle **100% 一致**，包含所有歷史封存資料。

1.  **Row Count Check (總筆數比對)**：
    - 編寫腳本自動比對 Oracle 與 PG 所有 Table 的 `COUNT(*)`。
    - **重點檢查**：歷史訂單表 (`GHIST_MN`)、交易明細表 (`GHIST_BILL`) 等大資料量表格，確保一筆未少。
2.  **Date Range Check (時間範圍比對)**：
    - 檢查 PG 中最早的一筆訂單日期 (`MIN(arrival_date)`) 是否與 Oracle 一致，證明 10 年前的資料也還在。
3.  **Sum Check (金額總和稽核)**：
    - 對金額欄位 (`amount`) 進行 SUM 比對，確保小數位數 (Precision) 轉換無誤，財務報表數字吻合。
4.  **功能與效能測試**：
    - 執行 `KTW-backend` 的關鍵流程 (入住、退房、查詢)，確認 API 回傳正確。
    - 針對重度查詢 (如報表) 執行 EXPLAIN ANALYZE，確認索引是否有效。

### 階段六：切換後的開發與維運 (Post-Migration Development)

**目標：** 在完成資料庫遷移後，無縫接軌開發工作，並確保 BOT 與 ADMIN 能即刻使用新資料庫。

1.  **架構優勢利用 (Architecture Benefit)**：
    目前系統架構為 `Oracle DB` -> `pms-api` -> `KTW-backend` -> `Line Bot / Admin Web`。
    - **關鍵策略**：我們只需 **重寫 `pms-api` 的資料存取層 (DAO)** 改接 PostgreSQL。
    - **極大優勢**：只要 `pms-api` 的 **API 輸出格式 (JSON)** 維持不變，上層的 `KTW-backend` (BOT核心) 和 `KTW-admin-web` (後台) **完全不需要大幅修改**，即可無痛切換。

2.  **開發環境配置**：
    - 將開發機 (Local) 的 `DB_CONNECTION` 字串從 Oracle 改為 PostgreSQL。
    - 導入 **Docker**：建議將 PostgreSQL database 容器化，讓開發者只需 `docker-compose up` 就能在本地擁有一模一樣的測試資料庫，不再依賴連線回公司內網的 Oracle。

3.  **新功能開發建議**：
    遷移後，新功能開發將不再受限於舊版 Oracle：
    - **全文搜尋**：利用 PG 的 `tsvector` 實作極速的客人姓名/備註搜尋 (取代緩慢的 SQL `LIKE %...%`)。
    - **JSONB 彈性欄位**：對於不確定的客人需求或標籤，可直接存入 JSONB 欄位，無需每次都開新欄位 (Schema-less 特性)。
    - **GIS 地理資訊**：若未來需做「附近景點推薦」或「客人來源分佈」，可直接啟用 PostGIS。

---

## 5. 常見風險與應對 (Risks & Solutions)

| 風險項目 | 應對方案 |
|:---|:---|
| **Stored Procedure 轉換失敗** | 使用 AI 輔助重寫，或將邏輯搬移至 Node.js Application 層 (現代化架構建議)。 |
| **資料亂碼 (Encoding)** | 確認 Oracle 為 AL32UTF8 或 ZHT16BIG5，PG 端務必使用 **UTF-8** 初始化 DB。 |
| **歷史髒資料 (Dirty Data)** | Oracle 對日期或數值檢查較寬鬆，舊資料可能存在 `0000-00-00` 或異常值。PG 較嚴格，需在匯出時寫 ETL script 清洗或修正。 |
| **效能不如預期** | PostgreSQL 的 Query Optimizer 與 Oracle 不同，可能需要重新設計索引或調整 SQL 寫法 (例如避免在 Where 條件左邊用函數)。 |
| **Sequence 不一致** | 上線前務必執行 `setval` 重置所有序列值。 |

---

## 6. Rollback 計畫 (回滾方案)

若切換當天發現致命錯誤，必須能在 30 分鐘內切回 Oracle。

1.  **雙寫機制 (選用)**：在 PG 上線初期，App 寫入 PG 成功後，非同步寫入 Oracle (作為備份)。
2.  **反向同步 (因應嚴重故障)**：
    若決定放棄 PG 切回 Oracle，這段期間在 PG 產生的新訂單資料，需人工或寫 Script 匯出並匯回 Oracle。
    *建議：上線初期保留 Oracle 唯讀權限，若 PG 掛掉，暫時切回 Oracle 唯讀模式供查詢，新訂單改用紙本或 Excel 暫記。*

---

## 7. 附錄：常用指令速查

### PostgreSQL 連線
```bash
psql -h localhost -U postgres -d pms_db
```

### 匯出資料 (pg_dump)
```bash
pg_dump -h localhost -U postgres -d pms_db -F c -f pms_backup.dump
```

### 匯入資料 (pg_restore)
```bash
pg_restore -h localhost -U postgres -d pms_db -v pms_backup.dump
```
