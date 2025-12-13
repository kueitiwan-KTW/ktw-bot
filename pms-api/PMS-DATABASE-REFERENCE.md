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

## 注意事項

1. **字元集問題**：Oracle 使用字元集 ID 871（繁體中文），Node.js 必須使用 **Thick 模式**
2. **TRIM 函數**：許多欄位有尾隨空格，查詢時建議使用 `TRIM()`
3. **日期欄位**：使用 `TRUNC()` 來比對日期（忽略時間）
4. **NULL 處理**：未填寫的欄位可能是 NULL，需要用 `COALESCE()` 或 `NVL()` 處理

---

*最後更新：2025-12-13*
*資料來源：PMS Server (192.168.8.3) - GDWUUKT Schema*
