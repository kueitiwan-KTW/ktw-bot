# PMS REST API

Oracle PMS 系統的 REST API 服務，為 LINE Bot 提供訂單查詢功能。

## 📋 功能

- ✅ 查詢訂單（依姓名或電話）
- ✅ 查詢單一訂單詳細資訊
- ✅ 查詢可用房間
- ⏸️ 建立新訂單（後續開發）
- ⏸️ 取消訂單（後續開發）

## 🚀 部署狀態

**部署日期**: 2025-12-10  
**部署位置**: Windows Server (192.168.8.3:3000)  
**狀態**: ✅ 運行中

### 測試結果
- ✅ 健康檢查: http://192.168.8.3:3000/api/health
- ✅ 查詢訂單: 成功返回 50 筆資料
- ✅ 訂單詳情: 完整資料含房型
- ✅ Mac 遠程訪問: 正常

## 🔧 快速開始（Windows Server）

### 前置條件
- ✅ Node.js v20.10.0
- ✅ Oracle Database 12c 運行中
- ✅ pms_api 帳號已創建

### 部署步驟

1. **安裝依賴**
   ```powershell
   cd C:\KTW-bot\pms-api
   npm install
   ```

2. **配置環境變數**
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   
   確認設定：
   ```env
   DB_USER=pms_api
   DB_PASSWORD=api123456
   DB_CONNECT_STRING=localhost:1521/gdwuukt
   ORACLE_CLIENT_LIB_DIR=D:\\app\\product\\12.2.0\\dbhome_1\\bin
   PORT=3000
   ```

3. **啟動服務**
   ```powershell
   npm start
   ```

## 📡 API 端點

### 健康檢查
```http
GET /api/health
```

**回應**:
```json
{
  "status": "ok",
  "timestamp": "2025-12-10T08:48:01.167Z",
  "service": "PMS API"
}
```

### 查詢訂單
```http
GET /api/bookings/search?name={name}
GET /api/bookings/search?phone={phone}
```

**參數**:
- `name`: 訂房人姓名（部分匹配）
- `phone`: 聯絡電話（部分匹配）

**回應**:
```json
{
  "success": true,
  "data": [
    {
      "booking_id": "00605101",
      "guest_name": "booking",
      "contact_phone": "886939157649",
      "check_in_date": "2025-02-22",
      "check_out_date": "2025-02-23",
      "nights": 1,
      "status_code": "D",
      "status_name": "已退房"
    }
  ],
  "count": 50
}
```

### 查詢訂單詳情
```http
GET /api/bookings/{booking_id}
```

**回應**:
```json
{
  "success": true,
  "data": {
    "booking_id": "00605101",
    "guest_name": "booking",
    "contact_phone": "886939157649",
    "check_in_date": "2025-02-22",
    "check_out_date": "2025-02-23",
    "nights": 1,
    "status_code": "D",
    "status_name": "已退房",
    "remarks": "...",
    "rooms": [
      {
        "room_type_code": "SQ",
        "room_type_name": null,
        "room_count": 1,
        "adult_count": 4,
        "child_count": 0
      }
    ]
  }
}
```

### 查詢可用房間
```http
GET /api/rooms/availability?check_in=2025-12-15&check_out=2025-12-17
```

**回應**:
```json
{
  "success": true,
  "data": {
    "check_in": "2025-12-15",
    "check_out": "2025-12-17",
    "rooms": [
      {
        "room_type_code": "ST",
        "room_type_name": "標準雙人房",
        "total_rooms": 10,
        "booked_rooms": 3,
        "available_rooms": 7,
        "is_available": true
      }
    ]
  }
}
```

## 🧪 測試

### 從 Windows Server 本地測試
```powershell
# 健康檢查
Invoke-WebRequest http://localhost:3000/api/health | Select-Object -ExpandProperty Content

# 查詢訂單
Invoke-WebRequest "http://localhost:3000/api/bookings/search?name=booking" | Select-Object -ExpandProperty Content
```

### 從 Mac 遠程測試
```bash
# 健康檢查
curl http://192.168.8.3:3000/api/health

# 查詢訂單
curl "http://192.168.8.3:3000/api/bookings/search?name=booking"

# 訂單詳情
curl http://192.168.8.3:3000/api/bookings/00605101
```

## 📝 技術棧

- **框架**: Express.js 4.18
- **資料庫**: Oracle Database 12c
- **ORM**: oracledb 6.0 (Thick 模式)
- **中間件**: cors, dotenv

## 🔍 重要配置

### Thick 模式設定
為支持中文字符集（GBK），必須使用 Thick 模式：

```javascript
oracledb.initOracleClient({ 
  libDir: process.env.ORACLE_CLIENT_LIB_DIR 
});
```

### 字符集問題解決
使用 `INSTR()` 函數替代 `LIKE` 以避免 ORA-12704 錯誤：

```sql
-- ❌ 錯誤
WHERE om.CUST_NAM LIKE '%' || :name || '%'

-- ✅ 正確
WHERE INSTR(om.CUST_NAM, :name) > 0
```

### CHAR 字段處理
IKEY 是 CHAR(10) 固定長度，需使用 TRIM：

```sql
WHERE TRIM(om.IKEY) = :booking_id
```

## 🔐 安全性

- 使用專用帳號 `pms_api`（僅查詢權限）
- 連線池管理，避免資源耗盡
- 輸入參數驗證
- 錯誤訊息不洩漏敏感資訊
- CORS 設定

## 📈 後續開發

- [ ] 建立訂單 API (POST /api/bookings)
- [ ] 取消訂單 API (DELETE /api/bookings/:booking_id)
- [ ] 使用 PM2 部署為 Windows 服務
- [ ] 日誌記錄優化
- [ ] API 認證機制
- [ ] 效能監控

## 🆘 常見問題

### API 啟動失敗

**問題**: Oracle Client 初始化失敗

**解決**: 檢查 `.env` 中的 `ORACLE_CLIENT_LIB_DIR` 路徑：
```
ORACLE_CLIENT_LIB_DIR=D:\\app\\product\\12.2.0\\dbhome_1\\bin
```

### 查詢失敗 ORA-12704

**問題**: character set mismatch

**解決**: 確認已使用 INSTR() 而非 LIKE，且已初始化 Thick 模式

### 連接被拒絕（遠程訪問）

**問題**: 從其他機器訪問失敗

**解決**: 檢查 Windows Server 防火牆是否開放 Port 3000

## 📚 相關文檔

- [POC 測試程式](../pms-api-poc/README.md)
- [Oracle 訪問全程記錄](../docs/oracle/oracle_access_journey.md)
- [PMS 資料庫結構](../docs/pms_database_structure.md)
- [API 規格](../docs/pms_api_specification.md)

## ✍️ 維護資訊

**創建日期**: 2025-12-10  
**最後更新**: 2025-12-10  
**維護者**: KTW Bot Team  
**版本**: 1.0.0
