# 德安資訊 PMS 資料庫結構分析

## 已探索的核心資料表

### 1. ORDER_MN - 訂單主檔
**用途**：儲存訂房的基本資訊

**關鍵欄位**：
| 欄位名稱 | 類型 | 說明 | 用於 API |
|---------|------|------|---------|
| `IKEY` | NCHAR(10) | 訂單編號（主鍵） | ✅ 訂單查詢 |
| `CI_DAT` | DATE | **入住日期** | ✅ 查詢可用房間 |
| `CO_DAT` | DATE | **退房日期** | ✅ 查詢可用房間 |
| `DAYS` | NUMBER(5) | 住宿天數 | ✅ |
| `CUST_NAM` | NVARCHAR2(80) | **客戶姓名** | ✅ 訂房記錄 |
| `CONTACT1_RMK` | NVARCHAR2(50) | **聯絡方式** | ✅ 訂房記錄 |
| `ORDER_STA` | NCHAR(1) | **訂單狀態** | ✅ 篩選有效訂單 |
| `GUEST_TYP` | NCHAR(4) | 客人類型 | |
| `ORDER_RMK` | NVARCHAR2(1000) | 訂單備註 | |
| `INS_DAT` | DATE | 建立日期 | |
| `INS_USR` | NVARCHAR2(10) | 建立人員 | |

---

### 2. ORDER_DT - 訂單明細
**用途**：儲存訂房的詳細資訊（房間、價格、人數）

**關鍵欄位**：
| 欄位名稱 | 類型 | 說明 | 用於 API |
|---------|------|------|---------|
| `IKEY` | NCHAR(10) | 訂單編號（外鍵 → ORDER_MN） | ✅ 關聯主檔 |
| `IKEY_SEQ_NOS` | NUMBER(5) | 明細序號 | |
| `ROOM_COD` | NCHAR(4) | **房間代碼** | ✅ 房型查詢 |
| `RATE_COD` | NCHAR(8) | 房價代碼 | |
| `ADULT_QNT` | NUMBER(5) | **成人數量** | ✅ 訂房需求 |
| `CHILD_QNT` | NUMBER(5) | **兒童數量** | ✅ 訂房需求 |
| `ORDER_QNT` | NUMBER(5) | **訂購房間數** | ✅ 房間數量 |
| `RENT_AMT` | NUMBER(15,3) | 房租金額 | ✅ 價格資訊 |
| `CI_DAT` | DATE | 入住日期 | |
| `CO_DAT` | DATE | 退房日期 | |

---

### 3. ROOM_RF - 房型參考檔
**用途**：定義房間類型（雙人房、四人房等）

**關鍵欄位**：
| 欄位名稱 | 類型 | 說明 | 用於 API |
|---------|------|------|---------|
| `ROOM_TYP` | NCHAR(4) | 房型代碼（主鍵） | ✅ 房型查詢 |
| `ROOM_NAM` | NVARCHAR2(10) | **房型名稱** | ✅ 顯示給客人 |
| `ROOM_SNA` | NVARCHAR2(4) | 房型簡稱 | |
| `ROOM_QNT` | NUMBER(5) | 該房型的房間總數 | ✅ 計算可用房 |

---

## 待探索的資料表

### ROOM_MN - 房間主檔
**預期用途**：實際房間編號（101、102 等）與狀態

### RMINV_MN / RMINV_DT - 房間庫存
**預期用途**：各日期的房間可用狀況

---

## 資料關聯圖

```
ORDER_MN (訂單主檔)
├─ IKEY (訂單編號)
├─ CI_DAT (入住日期)
├─ CO_DAT (退房日期)
├─ CUST_NAM (客戶姓名)
└─ CONTACT1_RMK (聯絡方式)
    │
    └─┬─ ORDER_DT (訂單明細)
        ├─ IKEY (關聯訂單主檔)
        ├─ ROOM_COD (房間代碼)
        ├─ ADULT_QNT (成人數)
        └─ ORDER_QNT (房間數)
            │
            └─┬─ ROOM_RF (房型參考)
                ├─ ROOM_TYP = ROOM_COD
                └─ ROOM_NAM (房型名稱)
```

---

## API 設計草案

基於已掌握的資料結構，可設計以下 API：

### 1. 查詢可用房間
```
GET /api/rooms/availability?check_in=2025-12-15&check_out=2025-12-17
```

**SQL 邏輯**：
```sql
SELECT r.ROOM_TYP, r.ROOM_NAM, r.ROOM_QNT
FROM TEST.ROOM_RF r
WHERE r.ROOM_TYP NOT IN (
    SELECT od.ROOM_COD 
    FROM TEST.ORDER_DT od
    JOIN TEST.ORDER_MN om ON od.IKEY = om.IKEY
    WHERE om.ORDER_STA != 'C'  -- 排除已取消
    AND (
        (om.CI_DAT <= :check_out AND om.CO_DAT >= :check_in)
    )
)
```

### 2. 建立訂房
```
POST /api/bookings
{
  "guest_name": "王小明",
  "contact_phone": "0912345678",
  "check_in": "2025-12-15",
  "check_out": "2025-12-17",
  "room_type": "雙人房",
  "adult_count": 2,
  "child_count": 0
}
```

**SQL 邏輯**：
```sql
-- 1. 插入 ORDER_MN
INSERT INTO TEST.ORDER_MN (IKEY, CI_DAT, CO_DAT, CUST_NAM, CONTACT1_RMK, ...)
VALUES (...)

-- 2. 插入 ORDER_DT
INSERT INTO TEST.ORDER_DT (IKEY, ROOM_COD, ADULT_QNT, CHILD_QNT, ...)
VALUES (...)
```

---

## 下一步
1. 查詢 ROOM_MN 結構
2. 查詢 RMINV_MN 結構
3. 確認訂單狀態代碼含義
4. 建立 Node.js API 服務
