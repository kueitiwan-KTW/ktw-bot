# PMS API 版本歷史

## [1.5] - 2025-12-11

### 欄位變更

#### ORDER_MN 表（訂單主檔）
**新增欄位**：
- 無新增欄位

**修改欄位格式**：
- `RVRESERVE_NOS`：OTA 訂單編號（支援 RMAG、RMPGP 前綴）
- `REMARKS`：備註欄位，現包含產品名稱資訊

**移除欄位**：
- 無移除欄位

#### ROOM_DETAILS（房型明細，由 API 動態生成）
**新增欄位**：
- `ROOM_TYPE_CODE`：房型代碼（大寫格式，如 "SD", "VD"）
- `ROOM_TYPE_NAME`：房型名稱（可能為 null）
- `ROOM_COUNT`：房間數量
- `ADULT_COUNT`：成人數
- `CHILD_COUNT`：兒童數
- `ROOM_RATE`：房價
- `ROOM_TOTAL`：房型小計
- `SERVICE_TOTAL`：服務費小計
- `TOTAL_AMOUNT`：總金額

### API 回應格式變更

#### GET /bookings/:booking_id

**V1.0 回應格式**：
```json
{
  "success": true,
  "data": {
    "booking_id": "00705501",
    "guest_name": "德安網路訂房",
    "rooms": [...]
  }
}
```

**V1.5 回應格式**（新增欄位）：
```json
{
  "success": true,
  "data": {
    "booking_id": "00705501",
    "ota_booking_id": "RMPGP250285738",  // 新增
    "guest_name": "德安網路訂房",
    "guest_first_name": "辰羽",  // 新增
    "guest_last_name": "張",  // 新增
    "contact_phone": "0967136192",
    "check_in_date": "2025-12-14",
    "check_out_date": "2025-12-15",
    "nights": 1,
    "status_code": "N",
    "status_name": "正常",
    "remarks": "2025-12-05 03:27:23 / 產品名稱: 官網優惠價SD...",  // 格式優化
    "deposit_due": 1280,
    "deposit_paid": 684,
    "room_numbers": [],
    "rooms": [
      {
        "ROOM_TYPE_CODE": "SD  ",  // 大寫格式
        "ROOM_TYPE_NAME": null,
        "ROOM_COUNT": 1,  // 大寫格式
        "ADULT_COUNT": 2,
        "CHILD_COUNT": 0,
        "ROOM_RATE": 2280,
        "ROOM_TOTAL": 2280,
        "SERVICE_TOTAL": 0,
        "TOTAL_AMOUNT": 0
      }
    ]
  }
}
```

### 字符集處理優化

**問題修復**：
- 解決 ORA-12704 字符集不匹配錯誤
- 實施分段查詢策略（PMS ID 和 OTA ID 分別查詢）
- JavaScript 層面進行狀態映射，避免 SQL 中的字符串比較

### 狀態代碼映射

**訂單狀態碼**（Oracle → 中文）：
- `N` → 正常
- `D` → 取消
- `W` → 等待
- `S` → NO-SHOW
- `I` → 已入住
- `O` → 已到

---

## [1.0] - 2025-12-09

### 初始版本
- 基本 CRUD API endpoints
- Oracle 資料庫連接
- 訂單查詢功能
- 支援 PMS ID 和 OTA ID 查詢
