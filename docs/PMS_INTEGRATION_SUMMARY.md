# PMS 整合套件總結文件

> **專案目標**：將德安資訊 PMS（Oracle Database）整合到 KTW-bot LINE BOT 系統

**建立日期**：2025-12-10  
**狀態**：✅ 資料庫探索完成 → ⏳ API 開發準備中

---

## 📋 今日成果總覽

### ✅ 已完成項目

1. **Oracle 資料庫連接**
   - 成功取得 OS 驗證存取權限
   - 資料庫：Oracle Database 12.2.0
   - SID：gdwuukt
   - 主機：gdwuukt-db01（本機）

2. **資料庫結構探索**
   - ORDER_MN（訂單主檔）- 訂房基本資訊
   - ORDER_DT（訂單明細）- 房間、價格、人數
   - ROOM_RF（房型參考）- 房型定義
   - ROOM_MN（房間主檔）- 實際房間狀態
   - RMINV_MN（房間庫存）- 每日可用房數

3. **API 規格設計**
   - 5 個核心 REST API 端點
   - 完整 SQL 查詢範例
   - JSON 資料格式定義
   - 錯誤處理機制

4. **整合方案規劃**
   - 確認採用方案 A：PMS API 為主要資料源
   - 設計 Next.js 後台架構
   - 規劃 BOT 資料流向

---

## 🗂️ 文件清單

所有文件位於：`/Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/`

| 文件名稱 | 用途 | 狀態 |
|---------|------|------|
| [task.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/task.md) | 任務清單與進度追蹤 | ✅ |
| [implementation_plan.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/implementation_plan.md) | 整體實作計畫 | ✅ |
| [pms_data_access_plan.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_data_access_plan.md) | PMS 資料存取計畫 | ✅ |
| [oracle_access_guide.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_access_guide.md) | Oracle 存取指南 | ✅ |
| [oracle_connection_steps.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_connection_steps.md) | Oracle 連線步驟 | ✅ |
| [oracle_sql_commands.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_sql_commands.md) | SQL 探索指令集 | ✅ |
| [pms_database_structure.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_database_structure.md) | 資料庫結構分析 | ✅ |
| [pms_api_specification.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_api_specification.md) | **REST API 完整規格** | ✅ |
| [bot_pms_integration_plan.md](file:///Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/bot_pms_integration_plan.md) | BOT 整合方案分析 | ✅ |

---

## 🏗️ KTW-bot 整合架構

### 最終架構圖

```
┌──────────────────────────────────────────────────────────┐
│                     KTW-bot 專案                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐              ┌──────────────────┐  │
│  │   LINE BOT      │              │  Next.js 後台    │  │
│  │   (Python)      │              │  (管理介面)      │  │
│  │                 │              │                  │  │
│  │ - 客人查詢訂單   │              │ - 訂單管理       │  │
│  │ - 天氣資訊      │              │ - 房況總覽       │  │
│  │ - FAQ 回應      │              │ - BOT 監控       │  │
│  └────────┬────────┘              └─────────┬────────┘  │
│           │                                 │            │
│           └────────────┬────────────────────┘            │
│                        │                                 │
│              ┌─────────▼──────────┐                      │
│              │   PMS REST API     │ ← 新增模組           │
│              │  (Node.js/Express) │                      │
│              │                    │                      │
│              │ GET /api/bookings  │                      │
│              │ GET /api/rooms     │                      │
│              │ POST /api/bookings │                      │
│              └─────────┬──────────┘                      │
│                        │                                 │
│                        ▼                                 │
│              ┌──────────────────┐                        │
│              │  Oracle Database │                        │
│              │  (PMS - 德安資訊)│                        │
│              │                  │                        │
│              │  - ORDER_MN      │                        │
│              │  - ORDER_DT      │                        │
│              │  - ROOM_RF       │                        │
│              └──────────────────┘                        │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 📦 建議的專案結構

```
KTW-bot/
├── bot.py                    # 現有 LINE BOT (修改：使用 PMS API)
├── app.py                    # 現有 Flask app
├── pms-api/                  # ← 新增：PMS API 模組
│   ├── package.json
│   ├── server.js             # Express 主程式
│   ├── config/
│   │   └── database.js       # Oracle 連線設定
│   ├── routes/
│   │   ├── bookings.js       # 訂單相關 API
│   │   └── rooms.js          # 房間相關 API
│   ├── controllers/
│   │   ├── bookingController.js
│   │   └── roomController.js
│   └── models/
│       ├── booking.js
│       └── room.js
├── admin-dashboard/          # ← 新增：Next.js 後台
│   ├── package.json
│   ├── pages/
│   │   ├── index.tsx         # 首頁（訂單總覽）
│   │   ├── bookings/
│   │   │   ├── index.tsx     # 訂單列表
│   │   │   └── [id].tsx      # 訂單詳情
│   │   └── rooms/
│   │       └── index.tsx     # 房況總覽
│   ├── components/
│   │   ├── BookingList.tsx
│   │   ├── RoomCalendar.tsx
│   │   └── BotMonitor.tsx
│   └── lib/
│       └── api.ts            # API 呼叫函式
├── docs/                     # ← 新增：整合文件
│   ├── pms_api_spec.md
│   ├── database_structure.md
│   └── integration_guide.md
└── README.md
```

---

## 🚀 整合步驟

### 階段 1：建立 PMS API（預計 2-3 天）

1. **初始化 Node.js 專案**
   ```bash
   cd KTW-bot
   mkdir pms-api && cd pms-api
   npm init -y
   npm install express oracledb dotenv cors
   ```

2. **實作 API 端點**（參考 `pms_api_specification.md`）
   - ✅ GET /api/bookings/search
   - ✅ GET /api/bookings/:id
   - ✅ GET /api/rooms/availability
   - ✅ POST /api/bookings
   - ✅ DELETE /api/bookings/:id

3. **測試 API**
   ```bash
   npm run dev
   curl http://localhost:3000/api/bookings/00150501
   ```

---

### 階段 2：調整 LINE BOT（預計 1 天）

**修改 `bot.py` 的 `check_order_status` 函式**：

```python
# 舊版（Gmail API）
def check_order_status(order_id):
    # 查詢 Gmail...
    pass

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

### 階段 3：建立 Next.js 後台（預計 3-4 天）

1. **初始化 Next.js 專案**
   ```bash
   cd KTW-bot
   npx create-next-app@latest admin-dashboard --typescript --tailwind
   ```

2. **實作核心頁面**
   - 訂單管理
   - 房況總覽
   - BOT 監控

3. **串接 PMS API**
   ```typescript
   // lib/api.ts
   export async function getBookings() {
     const res = await fetch('http://localhost:3000/api/bookings/search')
     return res.json()
   }
   ```

---

### 階段 4：部署（預計 1-2 天）

1. **PMS API 部署**
   - 部署到 Windows Server（與 PMS 同機）
   - 設定環境變數（Oracle 連線資訊）
   - 配置 PM2 或 Windows Service

2. **Next.js 後台部署**
   - Vercel（推薦）或自架伺服器
   - 配置 API 端點

3. **LINE BOT 更新**
   - 更新 API 端點到正式環境
   - 測試所有功能

---

## 🔑 關鍵資訊

### Oracle 連線配置

```javascript
// pms-api/config/database.js
module.exports = {
  user: 'system',
  password: process.env.DB_PASSWORD, // 使用環境變數
  connectString: 'gdwuukt-db01:1521/gdwuukt'
}
```

### 環境變數範例

```env
# .env
DB_PASSWORD=your_oracle_password
PORT=3000
NODE_ENV=production
```

---

## 📊 API 資料格式（給 BOT 使用）

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

## ⚠️ 注意事項

### 安全性
1. ✅ 使用 OS 驗證連接 Oracle（已設定 ORA_DBA 群組）
2. ⚠️ API 需要加入認證機制（API Key 或 JWT）
3. ⚠️ 環境變數不要提交到 Git
4. ✅ 使用參數化查詢防止 SQL Injection

### 效能
1. 建議使用連線池（oracledb.createPool）
2. 查詢結果可以加入快取（Redis）
3. API 回應時間應 < 500ms

### 備援
1. PMS API 故障時，BOT 可 fallback 到 Gmail
2. 資料庫定期備份
3. API 錯誤監控與告警

---

## 📞 後續支援

**需要協助時**，參考以下文件：
- API 開發：`pms_api_specification.md`
- 資料庫查詢：`pms_database_structure.md`
- Oracle 連線：`oracle_access_guide.md`

**下一步行動**：
1. ⏳ 建立 Node.js PMS API 專案
2. ⏳ 實作 5 個核心端點
3. ⏳ 測試 API 與 Oracle 連線
4. ⏳ 調整 LINE BOT 查詢邏輯
5. ⏳ 建立 Next.js 後台

---

## 🎯 專案目標達成指標

- [ ] LINE BOT 可透過 API 查詢訂單
- [ ] Next.js 後台可管理訂單
- [ ] API 回應時間 < 500ms
- [ ] 錯誤率 < 1%
- [ ] 完整的錯誤處理與日誌記錄

---

**建立日期**：2025-12-10  
**最後更新**：2025-12-10  
**狀態**：✅ 規劃完成，準備開發
