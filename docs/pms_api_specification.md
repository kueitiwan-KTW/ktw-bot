# PMS REST API 規格文件

## 概述

為 LINE BOT 提供完整的訂房查詢與管理 API，基於德安資訊 PMS Oracle 資料庫。

**資料庫資訊**：
- 系統：Oracle Database 12.2.0
- SID：gdwuukt
- Schema：TEST
- 主機：gdwuukt-db01 (本機)

---

## API 端點設計

### 1. 查詢客人訂單

**用途**：LINE BOT 讓客人查詢自己的訂房記錄

```
GET /api/bookings/search
```

**Query Parameters**：
| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `name` | string | 否 | 客人姓名（模糊搜尋） | 王小明 |
| `phone` | string | 否 | 聯絡電話 | 0912345678 |
| `booking_id` | string | 否 | 訂單編號 | 00150501 |

> 至少提供一個參數

**Response 200 OK**：
```json
{
  "success": true,
  "data": [
    {
      "booking_id": "00150501",
      "guest_name": "王小明",
      "contact_phone": "0920351552",
      "check_in_date": "2025-12-15",
      "check_out_date": "2025-12-17",
      "nights": 2,
      "status": "O",
      "status_name": "已確認",
      "rooms": [
        {
          "room_type": "雙人房",
          "room_count": 1,
          "adult_count": 2,
          "child_count": 0
        }
      ]
    }
  ]
}
```

**SQL 查詢**：
```sql
SELECT 
    om.IKEY as booking_id,
    om.CUST_NAM as guest_name,
    om.CONTACT1_RMK as contact_phone,
    om.CI_DAT as check_in_date,
    om.CO_DAT as check_out_date,
    om.DAYS as nights,
    om.ORDER_STA as status
FROM TEST.ORDER_MN om
WHERE 
    (om.CUST_NAM LIKE '%' || :name || '%' OR :name IS NULL)
    AND (om.CONTACT1_RMK = :phone OR :phone IS NULL)
    AND (om.IKEY = :booking_id OR :booking_id IS NULL)
ORDER BY om.INS_DAT DESC;
```

---

### 2. 查詢訂單詳情

**用途**：查詢特定訂單的完整資訊

```
GET /api/bookings/:booking_id
```

**Path Parameters**：
| 參數 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `booking_id` | string | 訂單編號 | 00150501 |

**Response 200 OK**：
```json
{
  "success": true,
  "data": {
    "booking_id": "00150501",
    "guest_name": "王小明",
    "contact_phone": "0920351552",
    "check_in_date": "2025-12-15",
    "check_out_date": "2025-12-17",
    "nights": 2,
    "status": "O",
    "status_name": "已確認",
    "created_at": "2025-12-01T10:30:00",
    "remarks": "提早入住",
    "rooms": [
      {
        "seq": 1,
        "room_type_code": "TWIN",
        "room_type_name": "雙人房",
        "room_count": 1,
        "adult_count": 2,
        "child_count": 0,
        "room_rate": 3000,
        "total_amount": 6000
      }
    ],
    "total_amount": 6000
  }
}
```

**SQL 查詢**：
```sql
-- 訂單主檔
SELECT 
    om.IKEY, om.CUST_NAM, om.CONTACT1_RMK, om.CI_DAT, om.CO_DAT,
    om.DAYS, om.ORDER_STA, om.INS_DAT, om.ORDER_RMK
FROM TEST.ORDER_MN om
WHERE om.IKEY = :booking_id;

-- 訂單明細
SELECT 
    od.IKEY_SEQ_NOS, od.ROOM_COD, od.ADULT_QNT, od.CHILD_QNT,
    od.ORDER_QNT, od.RENT_AMT, od.RENT_TOT,
    rf.ROOM_NAM
FROM TEST.ORDER_DT od
LEFT JOIN TEST.ROOM_RF rf ON od.ROOM_COD = rf.ROOM_TYP
WHERE od.IKEY = :booking_id
ORDER BY od.IKEY_SEQ_NOS;
```

---

### 3. 查詢可用房間

**用途**：查詢特定日期有哪些房型可訂

```
GET /api/rooms/availability
```

**Query Parameters**：
| 參數 | 類型 | 必填 | 說明 | 範例 |
|------|------|------|------|------|
| `check_in` | date | 是 | 入住日期 | 2025-12-15 |
| `check_out` | date | 是 | 退房日期 | 2025-12-17 |

**Response 200 OK**：
```json
{
  "success": true,
  "data": {
    "check_in": "2025-12-15",
    "check_out": "2025-12-17",
    "nights": 2,
    "available_rooms": [
      {
        "room_type_code": "TWIN",
        "room_type_name": "雙人房",
        "total_rooms": 10,
        "available_count": 3,
        "min_rate": 3000
      },
      {
        "room_type_code": "QUAD",
        "room_type_name": "四人房",
        "total_rooms": 5,
        "available_count": 2,
        "min_rate": 4500
      }
    ]
  }
}
```

**SQL 查詢**：
```sql
SELECT 
    ri.ROOM_COD,
    rf.ROOM_NAM,
    rf.ROOM_QNT as total_rooms,
    MIN(ri.LEFT_QNT) as available_count
FROM TEST.RMINV_MN ri
LEFT JOIN TEST.ROOM_RF rf ON ri.ROOM_COD = rf.ROOM_TYP
WHERE ri.BATCH_DAT BETWEEN :check_in AND :check_out - 1
GROUP BY ri.ROOM_COD, rf.ROOM_NAM, rf.ROOM_QNT
HAVING MIN(ri.LEFT_QNT) > 0
ORDER BY rf.ROOM_NAM;
```

---

### 4. 建立新訂單

**用途**：建立新的訂房記錄

```
POST /api/bookings
```

**Request Body**：
```json
{
  "guest_name": "王小明",
  "contact_phone": "0912345678",
  "check_in": "2025-12-15",
  "check_out": "2025-12-17",
  "rooms": [
    {
      "room_type_code": "TWIN",
      "room_count": 1,
      "adult_count": 2,
      "child_count": 0
    }
  ],
  "remarks": "提早入住"
}
```

**Response 201 Created**：
```json
{
  "success": true,
  "data": {
    "booking_id": "00150999",
    "message": "訂房成功"
  }
}
```

**SQL 插入**：
```sql
-- 1. 產生訂單編號
SELECT MAX(TO_NUMBER(IKEY)) + 1 FROM TEST.ORDER_MN;

-- 2. 插入訂單主檔
INSERT INTO TEST.ORDER_MN (
    IKEY, CUST_NAM, CONTACT1_RMK, CI_DAT, CO_DAT, DAYS,
    ORDER_STA, GUEST_WAY, SOURCE_TYP, GUEST_TYP, 
    CONFIRM_STA, MASTER_STA, IS_GROUP, ORDER_DEPOSIT,
    INS_DAT, INS_USR, HOTEL_COD, INS_HOTEL, VIP_STA, TAG_STA,
    IS_PRTCONFIRM, PRTCONFIRM_STA
) VALUES (
    :booking_id, :guest_name, :phone, :check_in, :check_out, :days,
    'O', 'W', 'WEB', 'FIT',
    'Y', 'N', 'N', 0,
    SYSDATE, 'API', '0001', '0001', 0, 'N',
    'N', 'N'
);

-- 3. 插入訂單明細
INSERT INTO TEST.ORDER_DT (
    IKEY, IKEY_SEQ_NOS, ROOM_COD, ADULT_QNT, CHILD_QNT, ORDER_QNT,
    CI_DAT, CO_DAT, DAYS, ORDER_STA, GUEST_WAY,
    INV_QNT, NOSHOW_QNT, ASSIGN_QNT, CI_QNT, BLOCK_QNT,
    OLD_RENT_AMT, RENT_AMT, RENT_TOT, OLD_SERV_AMT, SERV_AMT,
    SERV_TOT, OTHER_TOT, PAY_TOT, RENT_DIFF, ARRIVL_NOS,
    ADDROOM_STA, PARENT_IKEY_SEQ,
    INS_DAT, INS_USR, HOTEL_COD
) VALUES (
    :booking_id, 1, :room_type, :adult, :child, :room_count,
    :check_in, :check_out, :days, 'O', 'W',
    0, 0, 0, 0, 0,
    0, :rate, :total, 0, 0,
    0, 0, 0, 0, 0,
    'N', 0,
    SYSDATE, 'API', '0001'
);
```

---

### 5. 取消訂單

**用途**：取消已確認的訂單

```
DELETE /api/bookings/:booking_id
```

**Path Parameters**：
| 參數 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `booking_id` | string | 訂單編號 | 00150501 |

**Request Body**：
```json
{
  "cancel_reason": "客人臨時有事"
}
```

**Response 200 OK**：
```json
{
  "success": true,
  "message": "訂單已取消"
}
```

**SQL 更新**：
```sql
UPDATE TEST.ORDER_MN 
SET ORDER_STA = 'C',
    CANCEL_DAT = SYSDATE,
    CANCEL_USR = 'API',
    ORDER_RMK = ORDER_RMK || ' [取消原因: ' || :reason || ']'
WHERE IKEY = :booking_id;

UPDATE TEST.ORDER_DT
SET ORDER_STA = 'C',
    CANCEL_DAT = SYSDATE,
    CANCEL_USR = 'API'
WHERE IKEY = :booking_id;
```

---

## 訂單狀態代碼

| 代碼 | 名稱 | 說明 |
|------|------|------|
| `O` | 已訂房 | 訂單已確認，等待入住 |
| `S` | 已入住 | 客人已入住 |
| `D` | 已退房 | 客人已完成退房 |
| `C` | 已取消 | 訂單已取消 |

---

## 錯誤處理

### 標準錯誤格式
```json
{
  "success": false,
  "error": {
    "code": "BOOKING_NOT_FOUND",
    "message": "找不到訂單",
    "details": "訂單編號 00150501 不存在"
  }
}
```

### 常見錯誤代碼
| HTTP Status | Error Code | 說明 |
|-------------|------------|------|
| 400 | INVALID_PARAMETERS | 參數格式錯誤 |
| 404 | BOOKING_NOT_FOUND | 找不到訂單 |
| 409 | ROOM_NOT_AVAILABLE | 房間已滿 |
| 500 | DATABASE_ERROR | 資料庫錯誤 |

---

## 技術實作

### Node.js + Express + oracledb

**套件需求**：
```json
{
  "dependencies": {
    "express": "^4.18.0",
    "oracledb": "^6.0.0",
    "dotenv": "^16.0.0",
    "cors": "^2.8.5"
  }
}
```

**資料庫連線設定**：
```javascript
const oracledb = require('oracledb');

const dbConfig = {
  user: 'system',
  password: process.env.DB_PASSWORD,
  connectString: 'gdwuukt-db01:1521/gdwuukt'
};

async function getConnection() {
  return await oracledb.getConnection(dbConfig);
}
```

---

## 安全性考量

1. **唯讀 vs 讀寫權限**：
   - 查詢 API 使用唯讀帳號
   - 建立/取消訂單使用有限寫入權限的帳號

2. **SQL Injection 防護**：
   - 使用參數化查詢（Prepared Statements）
   - 永不直接拼接 SQL 字串

3. **API 認證**：
   - 建議使用 API Key 或 JWT Token
   - LINE BOT webhook 驗證簽章

4. **資料驗證**：
   - 驗證日期格式
   - 驗證電話號碼格式
   - 限制查詢結果數量

---

## 下一步

1. ✅ 資料庫結構分析完成
2. ✅ API 規格設計完成
3. ⏳ 建立 Node.js API 服務
4. ⏳ 部署測試環境
5. ⏳ 整合到 LINE BOT
