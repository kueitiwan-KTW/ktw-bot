# 德安資訊 PMS 資料擷取專案（Oracle 版）

## 專案目標

取得德安資訊 PMS 系統的資料存取權限，為後續 AI 語音訂房助理整合做準備。

**系統現況**：
- PMS 系統：德安資訊（台灣市佔率第一的飯店管理系統）
- 部署環境：本地 Windows Server 2016
- **資料庫系統：Oracle Database**
- 權限狀況：無資料庫存取權限
- 廠商關係：已終止合作，但擁有系統產權與所有權

## 技術方案概述

### 階段一：探勘與存取
目標是先取得 Oracle 資料庫的存取權限。

### 階段二：分析與整合
建立資料擷取 API，供 AI 語音助理使用。

---

## 實作步驟

### 階段一：取得資料庫存取權限

#### 步驟 1：確認 Oracle 資料庫版本與連線資訊

德安資訊 PMS 系統使用 **Oracle Database** 作為資料庫。

**行動方案**：
1. 登入 Windows Server 2016
2. 檢查是否安裝 SQL Server：
   - 開啟「服務」(services.msc)
   - 尋找 `SQL Server (MSSQLSERVER)` 或類似服務
3. 確認 SQL Server 版本與執行個體名稱

**預期發現**：
- SQL Server 2008/2012/2014/2016（依德安資訊系統版本而定)
- 預設執行個體 `MSSQLSERVER` 或自訂執行個體

---

#### 步驟 2：使用 Windows 管理員權限重設 SQL Server 密碼

由於您擁有伺服器的完整控制權，可以透過以下方式取得資料庫存取權限：

**方案 A：使用 Windows 驗證（推薦）**

如果您的 Windows 帳號具有本機管理員權限：

1. 安裝 SQL Server Management Studio (SSMS)
   ```powershell
   # 下載最新版 SSMS
   # https://aka.ms/ssmsfullsetup
   ```

2. 使用 Windows 驗證連接
   - 開啟 SSMS
   - 伺服器名稱：`localhost` 或 `.\MSSQLSERVER`
   - 驗證方式：選擇「Windows 驗證」
   - 點選「連接」

3. 檢查是否有 sysadmin 權限
   ```sql
   -- 檢查目前使用者權限
   SELECT IS_SRVROLEMEMBER('sysadmin');
   -- 結果為 1 表示有 sysadmin 權限
   ```

**方案 B：透過單一使用者模式重設 SA 密碼**

如果 Windows 驗證無法連接或沒有足夠權限：

1. 停止 SQL Server 服務
   - 開啟「SQL Server Configuration Manager」
   - 右鍵「SQL Server (MSSQLSERVER)」→ 停止

2. 設定單一使用者模式
   - 右鍵「SQL Server (MSSQLSERVER)」→ 內容
   - 點選「啟動參數」標籤
   - 新增參數：`-m;`
   - 點選「新增」→「確定」

3. 啟動 SQL Server 服務

4. 使用本機管理員身分連接
   ```powershell
   # 使用 sqlcmd
   sqlcmd -S localhost -E
   ```

5. 重設 SA 密碼並啟用帳號
   ```sql
   ALTER LOGIN sa WITH PASSWORD = 'YourNewStrongPassword123!';
   ALTER LOGIN sa ENABLE;
   GO
   ```

6. 移除單一使用者模式參數並重新啟動服務

---

#### 步驟 3：建立專用資料庫帳號

為了安全性，建議建立專用的唯讀帳號供 API 使用：

```sql
-- 建立新登入
CREATE LOGIN hotel_api_user WITH PASSWORD = 'SecurePassword123!';

-- 切換到 PMS 資料庫（資料庫名稱需實際確認）
USE [PMS_DatabaseName];

-- 建立資料庫使用者
CREATE USER hotel_api_user FOR LOGIN hotel_api_user;

-- 授予唯讀權限
ALTER ROLE db_datareader ADD MEMBER hotel_api_user;

-- 如需寫入訂房資料，授予特定表格的寫入權限
GRANT INSERT, UPDATE ON dbo.Reservations TO hotel_api_user;
```

---

### 階段二：分析資料庫結構

#### 步驟 4：探索資料庫架構

連接成功後，探索德安資訊 PMS 的資料庫結構：

```sql
-- 列出所有資料庫
SELECT name FROM sys.databases;

-- 切換到 PMS 資料庫
USE [找到的PMS資料庫名稱];

-- 列出所有資料表
SELECT TABLE_SCHEMA, TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

-- 查看特定表格結構（以訂房表為例）
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Reservations' -- 或可能是 Bookings, Orders 等
ORDER BY ORDINAL_POSITION;
```

#### 步驟 5：識別關鍵資料表

PMS 系統通常包含以下核心資料表（實際名稱需確認）:

**預期資料表**：
- **訂房/預訂**：`Reservations`, `Bookings`, `Orders`
- **客人資訊**：`Guests`, `Customers`
- **房間**：`Rooms`, `RoomTypes`
- **房態**：`RoomStatus`
- **帳務**：`Bills`, `Payments`, `Transactions`

**探索查詢**：
```sql
-- 尋找包含特定關鍵字的表格
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME LIKE '%book%' 
   OR TABLE_NAME LIKE '%reserv%'
   OR TABLE_NAME LIKE '%guest%'
   OR TABLE_NAME LIKE '%room%';

-- 查看資料表的記錄數
SELECT 
    t.NAME AS TableName,
    p.rows AS RowCounts
FROM sys.tables t
INNER JOIN sys.partitions p ON t.object_id = p.OBJECT_ID
WHERE p.index_id < 2
ORDER BY p.rows DESC;
```

---

### 階段三：建立資料擷取 API

#### 步驟 6：設計 REST API

建立一個 Node.js / Python API 服務，提供給 Dialogflow Webhook 使用。

**API 端點設計**：

```
GET  /api/rooms/availability?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD
POST /api/bookings
GET  /api/bookings/:id
PUT  /api/bookings/:id
```

**技術選擇**：
- **Node.js + Express + mssql**（推薦，快速開發）
- Python + FastAPI + pyodbc

#### 步驟 7：實作範例（Node.js）

```javascript
// server.js
const express = require('express');
const sql = require('mssql');

const app = express();
app.use(express.json());

// 資料庫連線設定
const config = {
  user: 'hotel_api_user',
  password: 'SecurePassword123!',
  server: 'localhost',
  database: 'PMS_DatabaseName',
  options: {
    encrypt: false,
    trustServerCertificate: true
  }
};

// 查詢可用房間
app.get('/api/rooms/availability', async (req, res) => {
  const { check_in, check_out, room_type } = req.query;
  
  try {
    const pool = await sql.connect(config);
    const result = await pool.request()
      .input('checkIn', sql.Date, check_in)
      .input('checkOut', sql.Date, check_out)
      .input('roomType', sql.NVarChar, room_type)
      .query(`
        SELECT r.RoomID, rt.TypeName, rt.BasePrice
        FROM Rooms r
        JOIN RoomTypes rt ON r.RoomTypeID = rt.RoomTypeID
        WHERE r.RoomID NOT IN (
          SELECT RoomID FROM Reservations
          WHERE (CheckInDate <= @checkOut AND CheckOutDate >= @checkIn)
          AND Status != 'Cancelled'
        )
        AND (@roomType IS NULL OR rt.TypeName = @roomType)
      `);
    
    res.json({ available: result.recordset });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database query failed' });
  }
});

// 建立訂房
app.post('/api/bookings', async (req, res) => {
  const { guest_name, contact_phone, check_in, check_out, room_type, guest_count } = req.body;
  
  try {
    const pool = await sql.connect(config);
    const result = await pool.request()
      .input('guestName', sql.NVarChar, guest_name)
      .input('phone', sql.NVarChar, contact_phone)
      .input('checkIn', sql.Date, check_in)
      .input('checkOut', sql.Date, check_out)
      .input('guestCount', sql.Int, guest_count)
      .input('roomType', sql.NVarChar, room_type)
      .query(`
        INSERT INTO BookingRequests 
        (GuestName, ContactPhone, CheckInDate, CheckOutDate, GuestCount, RoomType, Status, CreatedAt)
        VALUES 
        (@guestName, @phone, @checkIn, @checkOut, @guestCount, @roomType, 'pending', GETDATE());
        
        SELECT SCOPE_IDENTITY() AS BookingID;
      `);
    
    res.json({ 
      success: true, 
      booking_id: result.recordset[0].BookingID 
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to create booking' });
  }
});

app.listen(3000, () => {
  console.log('PMS API running on port 3000');
});
```

---

## 安全性考量

> [!CAUTION]
> **重要安全措施**

1. **最小權限原則**
   - API 帳號只授予必要的資料表存取權限
   - 使用唯讀權限查詢，只有必要欄位才給寫入權限

2. **密碼安全**
   - SA 密碼必須強度足夠（大小寫+數字+符號）
   - 定期更換密碼
   - 不要在程式碼中明碼儲存密碼（使用環境變數）

3. **網路安全**
   - API 服務僅內網存取，或使用 VPN
   - 啟用 HTTPS/TLS 加密連線
   - 考慮設定 IP 白名單

4. **資料備份**
   - 在進行任何操作前先備份資料庫
   - 定期備份以防資料遺失

---

## 驗證計畫

### 資料庫連線測試

```powershell
# 測試 SQL Server 連線
sqlcmd -S localhost -U hotel_api_user -P SecurePassword123! -Q "SELECT @@VERSION"
```

### API 功能測試

```bash
# 測試查詢可用房間
curl "http://localhost:3000/api/rooms/availability?check_in=2025-12-15&check_out=2025-12-17&room_type=雙人房"

# 測試建立訂房
curl -X POST http://localhost:3000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "guest_name": "測試客人",
    "contact_phone": "0912345678",
    "check_in": "2025-12-15",
    "check_out": "2025-12-17",
    "room_type": "雙人房",
    "guest_count": 2
  }'
```

---

## 風險與注意事項

> [!WARNING]
> **潛在風險**

1. **資料表名稱與結構不確定**
   - 德安資訊的實際資料表結構需要實際探索
   - 可能需要多次嘗試才能找到正確的欄位對應

2. **PMS 系統版本差異**
   - 不同版本的德安資訊系統可能有不同的資料庫結構

3. **營運中斷風險**
   - 在 PMS 營運時間進行資料庫操作可能影響正常作業
   - 建議在離峰時段或測試環境先行測試

4. **授權合規**
   - 雖然擁有產權，但建議確認軟體授權是否允許自行存取資料庫

---

## 預計時程

- **第 1 天**：取得 SQL Server 存取權限
- **第 2-3 天**：探索資料庫結構，識別關鍵資料表
- **第 4-5 天**：建立資料擷取 API
- **第 6-7 天**：測試與驗證

---

## 後續整合

完成 PMS 資料存取後，即可：
1. 更新 Dialogflow Webhook，整合即時房況查詢
2. 實現自動訂房功能（直接寫入 PMS）
3. 提供客人訂房確認與管理功能
