# PMS 資料庫欄位參考文檔

> 記錄 PMS (Oracle) 資料庫的重要資料表結構和欄位說明

---

## 🎯 重要發現：客戶備註系統

### GHIST_MN - 客戶歷史主檔 ⭐

> **用途**：存放客戶的歷史記錄和備註（跨訂單、永久保存）
>
> **關聯**：透過 `ID_NOS` (身分證號) 或 `ALT_NAM` (姓名) 關聯客人
>
> **特點**：備註會跟著客人，不管他住哪間房或哪次訂單

#### 關鍵欄位

| 欄位名 | 說明 | 範例值 | 備註 |
|--------|------|--------|------|
| **ID_NOS** | 身分證號 | A123182837 | 主要識別欄位 |
| **LAST_NAM** | 姓 | 郭 | |
| **FIRST_NAM** | 名 | 可驥 | |
| **ALT_NAM** | 姓名 | 郭可驥 | |
| **REQUST_RMK** | 客戶需求備註 | 副院長的教授 | ⭐ **客戶備註欄位** |
| **CHARACTER_RMK** | 個性備註 | NULL | 客人個性特徵 |
| **ANAMNESIS** | 病歷/過敏史 | NULL | 醫療相關資訊 |
| **CONTACT1_RMK** | 聯絡電話1 | 0919220815 | |
| **CONTACT2_RMK** | 聯絡電話2 | NULL | |
| **CONTACT3_RMK** | 聯絡電話3 | NULL | |
| **CONTACT4_RMK** | 聯絡電話4 | NULL | |
| **VISITDAT_NOS** | 來訪次數 | 0 | 累計住宿次數 |
| **FIRST_DAT** | 首次來訪日期 | NULL | |
| **LAST_DAT** | 最近來訪日期 | NULL | |
| **WEDDING_DAT** | 結婚紀念日 | NULL | |
| **BIRTH_DAT** | 生日 | 1966-10-28 | |
| **INS_DAT** | 建立日期 | 2025-12-13 17:22:06 | |
| **UPD_DAT** | 更新日期 | 2025-12-13 17:23:59 | |

#### 實際案例

```sql
SELECT * FROM GDWUUKT.GHIST_MN WHERE TRIM(ID_NOS) = 'A123182837'
```

結果：
```
姓名: 郭可驥
身分證: A123182837
REQUST_RMK: 副院長的教授  ← 客戶備註
建立時間: 2025-12-13 17:22:06
```

---

## GUEST_MN - 住客主檔

> **用途**：存放實際入住客人的詳細資料（含證件資訊）
>
> **關聯**：透過 `IKEY` (訂單號) 與 `ORDER_MN` 關聯

### 關鍵欄位

| 欄位名 | 說明 | 範例值 | 備註 |
|--------|------|--------|------|
| **ROOM_NOS** | 房號 | 606 | 實際入住房號 |
| **IKEY** | 訂單號 | 00708801 | 關聯到 ORDER_MN.IKEY |
| **IKEY_SEQ_NOS** | 訂單序號 | 1 | 同訂單多房時使用 |
| **ID_COD** | 身分證號 | M122076214 | 🔍 **可用於搜尋特定住客** |
| **FIRST_NAM** | 名（訂房） | Huang hua | 訂房時填寫的名字 |
| **LAST_NAM** | 姓（訂房） | Yen | 訂房時填寫的姓氏 |
| **ALT_NAM** | 實際登記姓名 | 洪榮宏 | ⭐ **證件掃描後的真實姓名** |
| **BIRTH_DAT** | 生日 | 1984-06-06 | 證件上的出生日期 |
| **SEX_TYP** | 性別 | M | M=男, F=女 |
| **CONTRY_COD** | 國籍 | TWN | 國家代碼 |
| **CONTACT1_COD** | 聯絡方式類型1 | 04 | 電話類型代碼 |
| **CONTACT1_RMK** | 聯絡電話1 | 0987090898 | 實際電話號碼 |
| **CI_DAT** | 入住日期 | 2025-12-13 | Check-in Date |
| **ACI_DAT** | 實際入住日期 | 2025-12-13 | Actual Check-in Date |
| **CI_TIM** | 入住時間 | 194018 | 19:40:18 |
| **RCO_DAT** | 預計退房日 | 2025-12-14 | Reservation Check-out Date |
| **ECO_DAT** | 預計退房日 | 2025-12-14 | Expected Check-out Date |
| **ACO_DAT** | 實際退房日 | NULL | Actual Check-out Date |
| **GUEST_STA** | 住客狀態 | O | O=入住中 |
| **GUEST_TYP** | 客人類型 | 04 | 類型代碼 |
| **RATE_COD** | 房價代碼 | OTAnfb | OTA non-breakfast |
| **ROOM_COD** | 房型代碼 | DD | 對應到 ROOM_RF |
| **GCUST_COD** | 客戶代碼 | HFD000000000670601 | |
| **CCUST_NAM** | 公司/訂房來源 | agoda | |
| **RENT_AMT** | 房租金額 | 2131 | 實際房價 |
| **SERV_AMT** | 服務費 | 0 | |
| **MASTER_NOS** | 主房號 | 606 | 多房關聯時使用 |
| **MASTER_STA** | 是否主房 | N | Y/N |
| **REMARK1** | 備註1 | OTA定價不含早... | 訂房備註 |
| **INS_USR** | 建立人員 | root | |
| **CAR_NOS** | 車號 | 5289 | 停車場車號 |

### 完整欄位列表

```
ROOM_NOS, ROOM_SER, GUEST_STA, RATE_COD, USE_COD, ROOM_COD, 
CI_DAT, ACI_DAT, CI_SER, CI_TIM, GCUST_COD, CCUST_COD, ACUST_COD, 
FIRST_NAM, LAST_NAM, ALT_NAM, GUEST_TYP, SEX_TYP, BIRTH_DAT, 
CONTRY_COD, ID_COD, CONTACT1_COD, CONTACT1_RMK, CONTACT2_COD, 
CONTACT2_RMK, CONTACT3_COD, CONTACT3_RMK, UNI_COD, ZIP_COD, 
CREDIT_NOS, EXPIRA_DAT, MASTER_NOS, MASTER_SER, IKEY, IKEY_SEQ_NOS, 
PSNGR_NOS, ACO_DAT, OUT_TIM, RCO_DAT, ECO_DAT, REMARK1, REMARK2, 
REMARK3, REMARK4, MASTER_STA, VA_STA, FLAG3_STA, FLAG4_STA, 
FLAG5_STA, PRECREDIT_AMT, INS_USR, CO_USR, SHARE_RAT, DEPOSIT_NOS, 
SYSTEM_TYP, CAR_NOS, OLD_RENT_AMT, RENT_AMT, OLD_SERV_AMT, 
SERV_AMT, UNI_TITLE, CCUST_NAM, CARRIERID2, CARRIERID1, 
CARRIERTYPE, NPOBAN, DONATEMARK, ACO_SYS_DAT, AIRLINE_COD, 
AIRMB_NOS, PERSONAL_APPRAISE, USE_DAILY_RATE
```

---

## ORDER_MN - 訂單主檔

> **用途**：存放訂房資料（訂房階段）
>
> **關聯**：透過 `IKEY` 與 `GUEST_MN` 關聯

### 關鍵欄位

| 欄位名 | 說明 | 範例值 | 備註 |
|--------|------|--------|------|
| **IKEY** | 訂單號 | 00708801 | 主鍵，關聯到 GUEST_MN |
| **RVRESERVE_NOS** | OTA訂單號 | RMAG1677888347 | 來自 Agoda/Booking 等 |
| **SOURCE_TYP** | 訂單來源 | OTA | OTA/電話/LINE等 |
| **CUST_NAM** | 顧客名稱 | agoda | 訂房來源 |
| **GLAST_NAM** | 訂房姓 | Yen | 訂房時的姓氏 |
| **GFIRST_NAM** | 訂房名 | Huang hua | 訂房時的名字 |
| **GALT_NAM** | 訂房全名 | Huang hua Yen | 組合後的全名 |
| **CONTACT1_RMK** | 聯絡電話 | 8860987090898 | |
| **CI_DAT** | 預計入住日 | 2025-12-13 | |
| **CO_DAT** | 預計退房日 | 2025-12-14 | |
| **DAYS** | 住宿天數 | 1 | |
| **ORDER_STA** | 訂單狀態 | I | N/O/I/D/C |
| **ORDER_RMK** | 訂單備註 | OTA定價不含早... | |
| **ORDER_DEPOSIT** | 訂金 | 2131 | |
| **CONFIRM_NOS** | 確認單號 | C0003884 | |
| **INS_DAT** | 建立日期 | 2025-12-13 01:16:00 | |
| **UPD_DAT** | 更新日期 | 2025-12-13 09:46:17 | |

### 訂單狀態代碼

| 代碼 | 說明 | 中文 |
|------|------|------|
| **N** | New Order | 新訂單 |
| **O** | Confirmed | 已確認 |
| **I** | Checked-In | 已入住 |
| **D** | Checked-Out | 已退房 |
| **C** | Cancelled | 已取消 |
| **R** | Reserved | 預約中 |

---

## ASSIGN_DT - 房間分配表

> **用途**：記錄房間分配歷史
>
> **關聯**：透過 `IKEY` 與訂單關聯，透過 `ROOM_NOS` 與房號關聯

### 欄位

| 欄位名 | 說明 | 範例值 |
|--------|------|--------|
| **KEY_NOS** | 分配序號 | 29527 |
| **ROOM_NOS** | 房號 | 606 |
| **BEGIN_DAT** | 開始日期 | 2025-12-13 |
| **END_DAT** | 結束日期 | 2025-12-13 |
| **CO_DAT** | 退房日 | 2025-12-14 |
| **STATUS_COD** | 狀態 | C/I | C/I=已入住, C/O=已退房 |
| **IKEY** | 訂單號 | 00708801 |
| **IKEY_SEQ_NOS** | 訂單序號 | 1 |
| **GUEST_WAY** | 客人類型 | F | |
| **ROOM_COD** | 房型代碼 | DD | |

---

## ORDER_DT - 訂單明細表

> **用途**：訂單的房型明細

| 欄位名 | 說明 |
|--------|------|
| **IKEY** | 訂單號 |
| **IKEY_SEQ_NOS** | 明細序號 |
| **ROOM_COD** | 房型代碼 |
| **ORDER_QNT** | 房間數量 |
| **ADULT_QNT** | 成人數 |
| **CHILD_QNT** | 小孩數 |
| **RENT_TOT** | 租金總額 |

---

## 資料表關聯圖

```
訂房流程：

1. 訂房階段
   ORDER_MN (訂單主檔)
   ├─ IKEY: 00708801
   ├─ GLAST_NAM: Yen (訂房姓名)
   ├─ GFIRST_NAM: Huang hua
   └─ ORDER_STA: N → O (新訂單 → 已確認)

2. 入住階段
   GUEST_MN (住客主檔)
   ├─ IKEY: 00708801 ← 關聯到 ORDER_MN
   ├─ LAST_NAM: Yen (訂房姓名)
   ├─ FIRST_NAM: Huang hua
   ├─ ALT_NAM: 洪榮宏 ⭐ (證件姓名)
   ├─ ID_COD: M122076214 (身分證)
   └─ ROOM_NOS: 606

   ASSIGN_DT (房間分配)
   ├─ IKEY: 00708801
   ├─ ROOM_NOS: 606
   └─ STATUS_COD: C/I (已入住)

3. 退房階段
   GUEST_MN.ACO_DAT 更新
   ORDER_MN.ORDER_STA → D (已退房)
```

---

## 常用查詢範例

### 1. 查詢今日入住客人（含證件姓名）

```sql
SELECT 
    om.IKEY as 訂單號,
    om.GLAST_NAM || om.GFIRST_NAM as 訂房姓名,
    gm.ALT_NAM as 登記姓名,
    gm.ID_COD as 身分證號,
    gm.ROOM_NOS as 房號,
    gm.CI_DAT as 入住日,
    gm.CONTACT1_RMK as 電話
FROM GDWUUKT.ORDER_MN om
LEFT JOIN GDWUUKT.GUEST_MN gm ON om.IKEY = gm.IKEY
WHERE TRUNC(om.CI_DAT) = TRUNC(SYSDATE)
AND om.ORDER_STA = 'I'
ORDER BY gm.ROOM_NOS
```

### 2. 用身分證號查詢住客

```sql
SELECT * 
FROM GDWUUKT.GUEST_MN 
WHERE TRIM(ID_COD) = 'M122076214'
```

### 3. 用房號查詢目前住客

```sql
SELECT 
    ROOM_NOS as 房號,
    LAST_NAM || FIRST_NAM as 訂房姓名,
    ALT_NAM as 登記姓名,
    ID_COD as 身分證,
    CI_DAT as 入住日,
    RCO_DAT as 預計退房
FROM GDWUUKT.GUEST_MN
WHERE TRIM(ROOM_NOS) = '606'
AND GUEST_STA = 'O'
```

### 4. 查詢訂單的房間分配歷史

```sql
SELECT 
    ROOM_NOS,
    BEGIN_DAT,
    CO_DAT,
    STATUS_COD
FROM GDWUUKT.ASSIGN_DT
WHERE TRIM(IKEY) = '00708801'
ORDER BY BEGIN_DAT DESC
```

---

## 其他重要資料表

### RSORDER_MN - 餐廳訂單主檔

- **FULL_NAM**: 訂餐人姓名
- **ID_NOS**: 身分證號
- **ORDER_NOS**: 關聯訂單號（如有）

### ROOM_RF - 房型參考表

- **ROOM_TYP**: 房型代碼 (如 DD, SD, ST)
- **ROOM_NAM**: 房型名稱

---

## ROOM_MN - 房間主檔 ⭐

> **用途**：存放每個實體房間的狀態（清潔、停用、入住等）
>
> **關聯**：透過 `ROOM_NOS`（房號）與 GUEST_MN 關聯

### 清潔狀態相關欄位

| 欄位名 | 類型 | 說明 | 範例值 |
|--------|------|------|--------|
| **ROOM_NOS** | NCHAR | 房號 | 201, 606 |
| **FLOOR_NOS** | NCHAR | 樓層 | 2, 6 |
| **ROOM_COD** | NCHAR | 房型代碼 | SQ, SD, DD |
| **ROOM_STA** | NCHAR | 房間狀態 | V=空房, O=入住中 |
| **CLEAN_STA** | NCHAR | ⭐ **清潔狀態** | **C=乾淨, D=髒, I=待檢查** |
| **OOS_STA** | NCHAR | ⭐ **停用狀態** | **N=正常, Y=停用/維修** |
| **OSRESON_RMK** | NVARCHAR2 | 停用原因 | "門檔斷掉" |
| **ASSIGN_STA** | NCHAR | 分配狀態 | N |
| **CI_DAT** | DATE | 入住日期 | 2025-12-14 |
| **CO_DAT** | DATE | 退房日期 | 2025-12-15 |

### 人數相關欄位

| 欄位名 | 說明 |
|--------|------|
| **ADULT_QNT** | 成人數 |
| **CHILD_QNT** | 兒童數 |
| **BABY_QNT** | 嬰兒數 |
| **WOMAN_QNT** | 女性數 |
| **AEXBED_QNT** | 成人加床數 |
| **CEXBED_QNT** | 兒童加床數 |

### 其他欄位

| 欄位名 | 說明 |
|--------|------|
| **CHARACTER_RMK** | 房間備註（如"一大二小"）|
| **USER_RMK** | 使用者備註 |
| **BED_STA** | 床位狀態 |
| **ALARM_TIM** | 鬧鐘時間 |
| **ALARM_DAT** | 鬧鐘日期 |
| **CO_CLEAN_PTS** | 退房清潔積分 |
| **STAY_CLEAN_PTS** | 續住清潔積分 |
| **INS_DAT/INS_USR** | 建立日期/人員 |
| **UPD_DAT/UPD_USR** | 更新日期/人員 |

### 清潔狀態代碼對照

| 代碼 | 說明 | 中文 | 顏色建議 |
|------|------|------|---------|
| **C** | Clean | 乾淨 | 🟢 綠色 |
| **D** | Dirty | 髒（待清掃）| 🔴 紅色 |
| **I** | Inspecting | 待檢查 | 🟡 黃色 |

### 房間狀態代碼對照

| 代碼 | 說明 | 中文 |
|------|------|------|
| **V** | Vacant | 空房 |
| **O** | Occupied | 入住中 |

### 查詢範例

```sql
-- 查詢所有房間清潔狀態
SELECT 
    ROOM_NOS as 房號,
    ROOM_COD as 房型,
    ROOM_STA as 房間狀態,
    CLEAN_STA as 清潔狀態,
    OOS_STA as 停用狀態,
    OSRESON_RMK as 停用原因
FROM GDWUUKT.ROOM_MN
ORDER BY ROOM_NOS

-- 查詢需要清掃的房間
SELECT ROOM_NOS 
FROM GDWUUKT.ROOM_MN 
WHERE CLEAN_STA = 'D' AND OOS_STA = 'N'

-- 查詢維修中的房間
SELECT ROOM_NOS, OSRESON_RMK 
FROM GDWUUKT.ROOM_MN 
WHERE OOS_STA = 'Y'
```

---

## 注意事項

1. **字元集問題**：Oracle 使用字元集 ID 871（繁體中文），Node.js 必須使用 **Thick 模式**
2. **TRIM 函數**：許多欄位有尾隨空格，查詢時建議使用 `TRIM()`
3. **日期欄位**：使用 `TRUNC()` 來比對日期（忽略時間）
4. **NULL 處理**：未填寫的欄位可能是 NULL，需要用 `COALESCE()` 或 `NVL()` 處理

---

## WRS_STOCK_DT - 網路庫存表 ⭐

> **用途**：管理放到網路（OTA）上的房間庫存
>
> **WRS 鎖控**：PMS 系統的庫存控制機制，區分「網路庫存」與「館內庫存」

### 關鍵欄位

| 欄位名 | 類型 | 說明 | 備註 |
|--------|------|------|------|
| **HOTEL_COD** | NCHAR(12) | 飯店代碼 | 固定 '01' |
| **ROOM_COD** | NCHAR(12) | 房型代碼 | SD, CD, WD... |
| **BATCH_DAT** | DATE | 日期 | 查詢條件 |
| **STOCK_QNT** | NUMBER | ⭐ **網路總庫存** | 放到 OTA 的數量 |
| **USE_QNT** | NUMBER | 已訂數量 | OTA 已訂走的 |
| **UPLOAD_STA** | NCHAR(3) | 上傳狀態 | Y=已同步到網路 |
| **AUTO_STOCK_STA** | NCHAR(3) | 自動控管 | Y=自動庫存管理 |

### 計算公式

```
網路可預訂數 = STOCK_QNT - USE_QNT
```

### 查詢範例

```sql
-- 查詢今日各房型網路庫存
SELECT 
    TRIM(ROOM_COD) as 房型,
    STOCK_QNT as 網路庫存,
    USE_QNT as 已訂,
    (STOCK_QNT - USE_QNT) as 可訂
FROM GDWUUKT.WRS_STOCK_DT 
WHERE TRUNC(BATCH_DAT) = TRUNC(SYSDATE)
ORDER BY ROOM_COD
```

---

## RMINV_MN - 房間庫存主檔 ⭐

> **用途**：記錄各房型的完整庫存狀況（館內層級）
>
> **特點**：包含總房數、館內剩餘、停用房、已訂等完整資訊

### 關鍵欄位

| 欄位名 | 類型 | 說明 | 備註 |
|--------|------|------|------|
| **HOTEL_COD** | NCHAR | 飯店代碼 | 固定 '01' |
| **BATCH_DAT** | DATE | 日期 | 查詢條件 |
| **ROOM_COD** | NCHAR | 房型代碼 | SD, CD, WD... |
| **ROOM_QNT** | NUMBER | 房型總房數 | 實體房間數 |
| **LEFT_QNT** | NUMBER | ⭐ **館內剩餘庫存** | 櫃檯可用數 |
| **OOO_QNT** | NUMBER | 停用/維修房數 | Out of Order |
| **ORDER_QNT** | NUMBER | 已預訂數 | 總預訂數 |
| **USE_QNT** | NUMBER | 使用中 | 目前入住數 |
| **BLOCK_QNT** | NUMBER | 控房數 | 被鎖定的房 |
| **REST_QNT** | NUMBER | 剩餘 | - |

### 查詢範例

```sql
-- 查詢今日各房型館內庫存
SELECT 
    TRIM(ROOM_COD) as 房型,
    ROOM_QNT as 總房數,
    LEFT_QNT as 館內剩餘,
    OOO_QNT as 停用
FROM GDWUUKT.RMINV_MN 
WHERE TRUNC(BATCH_DAT) = TRUNC(SYSDATE)
ORDER BY ROOM_COD
```

---

## 庫存系統總結

### 庫存類型對照表

| 庫存類型 | 資料表 | 欄位 | 說明 |
|----------|--------|------|------|
| 🌐 **網路庫存** | `WRS_STOCK_DT` | `STOCK_QNT` | 放到 OTA 的總數 |
| 🌐 **網路可訂** | `WRS_STOCK_DT` | `STOCK_QNT - USE_QNT` | 網路實際可訂 |
| 🏨 **館內庫存** | `RMINV_MN` | `LEFT_QNT` | 櫃檯可用數量 |
| 📊 **總房數** | `RMINV_MN` | `ROOM_QNT` | 房型實體房間 |
| 🔧 **停用房** | `RMINV_MN` | `OOO_QNT` | 維修中房間 |

### 庫存邏輯說明

1. **網路庫存**：由館方主動「放上去」給 OTA 販售
2. **館內庫存**：PMS 自動計算的剩餘可用房間
3. **WRS 鎖控**：控制網路庫存的機制，可隨時拉回

---

## WRS_ROOM_PRICE - 房間價格表 ⭐

> **用途**：記錄各房型按日期的價格（浮動定價）
>
> **特點**：週末/假日可設定不同價格

### 關鍵欄位

| 欄位名 | 類型 | 說明 | 備註 |
|--------|------|------|------|
| **CI_DAT** | DATE | 入住日期 | 查詢條件 |
| **ROOM_COD** | NCHAR | 房型代碼 | SD, CD, WD... |
| **PAY_TOT** | NUMBER | ⭐ **房價總額** | 含稅價格 |
| **DAYS** | NUMBER | 天數 | 當日預訂用 DAYS=1 |
| **PRODUCT_NOS** | NCHAR | 產品編號 | 20001901=官網優惠價 |

### 查詢範例

```sql
-- 查詢今日各房型價格（官網優惠價）
SELECT 
    TRIM(ROOM_COD) as 房型,
    PAY_TOT as 價格
FROM GDWUUKT.WRS_ROOM_PRICE 
WHERE TRUNC(CI_DAT) = TRUNC(SYSDATE)
  AND DAYS = 1
  AND TRIM(PRODUCT_NOS) = '20001901'
ORDER BY ROOM_COD
```

### 價格來源優先順序

1. **WRS_ROOM_PRICE** (按日期浮動價) - `PRODUCT_NOS = '20001901'`
2. **RATECOD_DT** (固定價) - `RATE_COD = 'web001'`

---

## 已知問題與限制

### 退房還原訂單的姓名顯示

**問題描述**：
- 經過「退房 → 還原」操作的訂單，`GALT_NAM` 欄位可能因 Oracle NCHAR 固定長度特性導致空值檢查失效
- 即使 `LENGTH(TRIM(GALT_NAM)) > 0` 仍可能無法正確取得姓名

**影響範圍**：
- 少數經過退房還原的訂單
- 顯示為 `CUST_NAM`（如「電話或Line訂房」）而非實際姓名

**暫不處理**：
- 此情況發生機率極低
- 不影響正常訂單流程
- 已記錄供未來參考

**範例訂單**：00709801

---


---

## OTA 訂單編號前綴對照

| 前綴 | 訂房來源 |
|:-----|:---------|
| RMAG | Agoda |
| RMBK | Booking.com |
| RMEX | Expedia |
| RMCPT | 攜程 |
| RMPGP | 德安官網 |
| 無OTA編號 | 手KEY |

---

*最後更新：2025-12-17*
*資料來源：PMS Server (192.168.8.3) - GDWUUKT Schema*
