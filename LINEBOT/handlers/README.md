# Handlers 模組

> LINE Bot 訊息處理器集合

## 📋 模組說明

此資料夾包含所有訊息處理器（Handler），每個處理器負責特定類型的對話流程。

## 📂 檔案結構

| 檔案 | 說明 |
|:---|:---|
| `base_handler.py` | 基礎類別和路由器 |
| `order_query_handler.py` | 訂單查詢處理器 |
| `same_day_booking.py` | 當日預訂處理器 |
| `ai_conversation_handler.py` | 一般 AI 對話處理器 |

## 🔄 處理器流程

```
用戶訊息
    ↓
HandlerRouter (路由判斷)
    ├─ 有訂單編號 → OrderQueryHandler
    ├─ 訂房意圖 → SameDayBookingHandler  
    └─ 其他 → AIConversationHandler
```

## 📊 處理器對照表

| 處理器 | 觸發條件 | 寫入目標 |
|:---|:---|:---|
| `OrderQueryHandler` | 5+位數字 | `guest_orders.json` |
| `SameDayBookingHandler` | 訂房關鍵字 | `same_day_bookings.json` |
| `AIConversationHandler` | 一般問答 | 對話紀錄 |

## 🔧 使用方式

```python
from handlers import (
    HandlerRouter,
    OrderQueryHandler,
    SameDayBookingHandler,
    AIConversationHandler
)
```

---

*最後更新：2025-12-17*
