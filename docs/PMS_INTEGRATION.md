# PMS 整合完整指南（PMS Integration Guide，飯店管理系統整合指南）

> **專案目標**：建立 KTW Hotel LINE Bot（聊天機器人）與 PMS（飯店管理系統）的整合介面
>
> ⚠️ **歷史參考**：此文檔整合自 `PMS_INTEGRATION_SUMMARY.md` 和 `bot_pms_integration_plan.md`。**方案 A 已實施**，PMS API 現為主要資料源。

---

## 1. 整合方案分析

### 1.1 LINE BOT 原始架構

- 資料來源：Gmail API（查詢訂單郵件）
- 查詢方式：透過訂單編號搜尋郵件
- 顯示資訊：從郵件內容解析訂單詳情

### 1.2 PMS 資料庫現況

- 系統：Oracle Database 12.2.0
- SID：gdwuukt
- 主機：gdwuukt-db01
- 核心資料表：
  - ORDER_MN（訂單主檔）- 訂房基本資訊
  - ORDER_DT（訂單明細）- 房間、價格、人數
  - ROOM_RF（房型參考）- 房型定義
  - ROOM_MN（房間主檔）- 實際房間狀態
  - RMINV_MN（房間庫存）- 每日可用房數

---

## 2. 方案比較

### 方案 A：API 作為主要資料源 ✅ 已採用

```
LINE BOT → PMS REST API → Oracle Database → 回傳訂單資料
```

**優點**：

- ✅ 資料即時：直接查詢 PMS 官方資料庫
- ✅ 資料完整：可取得所有訂單欄位
- ✅ 資料一致：無同步問題
- ✅ 未來擴充性：可串接其他功能

**缺點**：

- ⚠️ 需要建立 REST API 服務
- ⚠️ 需要維護 API 服務

### 方案 B：Gmail + API 雙軌並行

```
LINE BOT → 優先查詢 Gmail
         ↓ 找不到
         → 查詢 PMS API
```

**缺點**：資料可能不同步、維護複雜度高

### 方案 C：維持 Gmail，PMS 僅供後台

- BOT 無整合效益，功能受限

---

## 3. 最終架構

```
┌──────────────────────────────────────────────────────────┐
│                     KTW-bot 專案                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐              ┌──────────────────┐   │
│  │   LINE BOT      │              │  Next.js 後台    │   │
│  │   (Python)      │              │  (管理介面)      │   │
│  │                 │              │                  │   │
│  │ - 客人查詢訂單   │              │ - 訂單管理       │   │
│  │ - 天氣資訊      │              │ - 房況總覽       │   │
│  │ - FAQ 回應      │              │ - BOT 監控       │   │
│  └────────┬────────┘              └─────────┬────────┘   │
│           │                                 │             │
│           └────────────┬────────────────────┘             │
│                        │                                  │
│              ┌─────────▼──────────┐                       │
│              │   PMS REST API     │                       │
│              │  (Node.js/Express) │                       │
│              │                    │                       │
│              │ GET /api/bookings  │                       │
│              │ GET /api/rooms     │                       │
│              │ POST /api/bookings │                       │
│              └─────────┬──────────┘                       │
│                        │                                  │
│                        ▼                                  │
│              ┌──────────────────┐                         │
│              │  Oracle Database │                         │
│              │  (PMS - 德安資訊)│                         │
│              │                  │                         │
│              │  - ORDER_MN      │                         │
│              │  - ORDER_DT      │                         │
│              │  - ROOM_RF       │                         │
│              └──────────────────┘                         │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 4. BOT 需要的訂單欄位

### 必要欄位

| 欄位名稱 | PMS 對應欄位                             | 說明            |
| -------- | ---------------------------------------- | --------------- |
| 訂單編號 | `ORDER_MN.IKEY`                          | 主鍵            |
| 訂房人   | `ORDER_MN.CUST_NAM`                      | 客人姓名        |
| 訂房來源 | `ORDER_MN.SOURCE_TYP`                    | Agoda/官網等    |
| 入住日期 | `ORDER_MN.CI_DAT`                        | Check-in        |
| 退房日期 | `ORDER_MN.CO_DAT`                        | Check-out       |
| 住宿晚數 | `ORDER_MN.DAYS`                          | 計算天數        |
| 房型     | `ORDER_DT.ROOM_COD` + `ROOM_RF.ROOM_NAM` | 雙人房/四人房等 |
| 房間數量 | `ORDER_DT.ORDER_QNT`                     | X 間            |

### 選用欄位

| 欄位名稱 | PMS 對應欄位            | 說明                 |
| -------- | ----------------------- | -------------------- |
| 成人數   | `ORDER_DT.ADULT_QNT`    | X 人                 |
| 兒童數   | `ORDER_DT.CHILD_QNT`    | X 人                 |
| 聯絡電話 | `ORDER_MN.CONTACT1_RMK` | 查詢用               |
| 訂單狀態 | `ORDER_MN.ORDER_STA`    | 已確認/已入住/已退房 |

---

## 5. API 資料格式

**查詢訂單響應**：

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
    "rooms": [
      {
        "room_type": "雙人房",
        "room_count": 1,
        "adult_count": 2,
        "child_count": 0
      }
    ]
  }
}
```

---

## 6. BOT 整合程式碼範例

```python
# 新版（PMS API）
import requests

def check_order_status(order_id):
    try:
        response = requests.get(f'http://localhost:3000/api/bookings/{order_id}')
        data = response.json()

        if data['success']:
            booking = data['data']
            return format_booking_message(booking)
        else:
            return "找不到訂單"
    except Exception as e:
        # Fallback to Gmail if API fails
        return check_order_gmail(order_id)
```

---

## 7. Oracle 連線配置

```javascript
// pms-api/config/database.js
module.exports = {
  user: "system",
  password: process.env.DB_PASSWORD,
  connectString: "gdwuukt-db01:1521/gdwuukt",
};
```

---

## 8. 安全性與效能

### 安全性

- ✅ 使用 OS 驗證連接 Oracle
- ⚠️ API 需要加入認證機制（API Key 或 JWT）
- ✅ 使用參數化查詢防止 SQL Injection

### 效能

- 使用連線池（oracledb.createPool）
- API 回應時間應 < 500ms

---

## 9. 完成狀態

- [x] Oracle 資料庫連接
- [x] 資料庫結構探索
- [x] API 規格設計
- [x] PMS REST API 建立
- [x] LINE BOT 整合

---

**維護者**：KTW Hotel IT Team
