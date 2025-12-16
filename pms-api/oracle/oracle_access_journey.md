# Oracle PMS 數據庫訪問權限取得全程記錄

> **文件目的**：完整記錄從零開始到成功訪問德安 PMS Oracle 數據庫的全過程，包含所有關鍵發現、問題排查和解決方案。

---

## 📅 時間線

**日期**：2025-12-10  
**總耗時**：約 2 小時  
**最終結果**：✅ 成功建立連接並查詢真實訂單資料

---

## 🎯 初始目標

解決 LINE Bot 的「幻覺」問題：
- **問題根源**：Gemini LLM 解析 Gmail HTML 郵件時提取資訊錯誤
- **解決方案**：直接查詢 PMS 數據庫獲取真實訂單資料
- **技術方案**：建立 Oracle PMS REST API

---

## 🔍 階段一：環境探索（30分鐘）

### 1.1 初始資訊收集

**已知資訊**（來自 pms-integration 分支）：
- 數據庫類型：Oracle Database 12c
- SID：`gdwuukt`
- Schema：`TEST`（❌ 後來發現這是錯誤的）
- 主機：`gdwuukt-db01`（❌ 實際在本機）
- 端口：`1521`

### 1.2 首次連接嘗試（Mac 端）

**嘗試方式**：使用 OS 驗證
```javascript
const dbConfig = {
  externalAuth: true,
  connectString: 'gdwuukt-db01:1521/gdwuukt'
};
```

**結果**：❌ 失敗  
**原因**：Mac 無法使用 Windows Server 的 OS 驗證

**關鍵發現 #1**：需要在 Windows Server 本機執行測試

---

## 🔧 階段二：Windows Server 設定（45分鐘）

### 2.1 Node.js 安裝

**問題**：Windows Server 未安裝 Node.js

**解決步驟**：
1. 下載 Node.js v20.10.0 (LTS)
2. 安裝過程中未勾選「Tools for Native Modules」
3. 安裝後 PATH 未自動設定

**PATH 問題解決**：
```powershell
$env:Path += ";C:\Program Files\nodejs"
```

### 2.2 Oracle 環境變數設定

**第一次嘗試**：設定 ORACLE_HOME 到 C:\app
```powershell
$env:ORACLE_HOME = "C:\app\product\12.2.0\client_1"
$env:ORACLE_SID = "gdwuukt"
```

**結果**：❌ ORA-12560（TNS: protocol adapter error）

**關鍵發現 #2**：找到了 Oracle Client，但需要的是 Oracle Database Server

### 2.3 尋找正確的 Oracle 路徑

**查找命令**：
```powershell
Get-WmiObject win32_service | Where-Object {$_.Name -eq "OracleServiceGDWUUKT"}
```

**輸出結果**：
```
PathName: d:\app\product\12.2.0\dbhome_1\bin\ORACLE.EXE GDWUUKT
```

**關鍵發現 #3**：Oracle Database 實際在 **D:\** 盤！

**正確設定**：
```powershell
$env:ORACLE_SID = "gdwuukt"
$env:ORACLE_HOME = "d:\app\product\12.2.0\dbhome_1"
```

**結果**：✅ 成功連接！
```
SQL*Plus: Release 12.2.0.1.0 Production
Connected to: Oracle Database 12c Standard Edition Release 12.2.0.1.0
```

---

## 🔐 階段三：帳號與權限（20分鐘）

### 3.1 創建專用 API 帳號

**原因**：
- 不使用 system 或 sys（安全性考量）
- OS 驗證在 Node.js oracledb Thin 模式下支援有限

**創建步驟**：
```sql
-- 以 sysdba 身分連接
sqlplus / as sysdba

-- 創建帳號
CREATE USER pms_api IDENTIFIED BY api123456;

-- 授予基本權限
GRANT CONNECT, RESOURCE TO pms_api;

-- 授予查詢權限
GRANT SELECT ANY TABLE TO pms_api;
```

### 3.2 發現真實的 Schema

**初始假設**：資料在 `TEST` schema  
**實際查詢**：
```sql
SELECT OWNER, TABLE_NAME, NUM_ROWS 
FROM ALL_TABLES 
WHERE TABLE_NAME = 'ORDER_MN'
ORDER BY OWNER;
```

**查詢結果**：
| OWNER   | TABLE_NAME | NUM_ROWS |
|---------|-----------|----------|
| DEMO    | ORDER_MN  | 171      |
| GDWUUKT | ORDER_MN  | 1566     |
| TEST    | ORDER_MN  | (NULL)   |

**關鍵發現 #4**：
- ✅ **GDWUUKT** 是正式環境（1566 筆訂單）
- ⚠️ **TEST** 是測試環境（幾乎沒資料）
- ℹ️ **DEMO** 是德安示範資料

### 3.3 授權訪問正式環境

```sql
GRANT SELECT ON GDWUUKT.ORDER_MN TO pms_api;
GRANT SELECT ON GDWUUKT.ORDER_DT TO pms_api;
GRANT SELECT ON GDWUUKT.ROOM_RF TO pms_api;
```

---

## 🐛 階段四：技術問題排查（25分鐘）

### 4.1 CHAR 字段空格問題

**問題現象**：
```javascript
// 查詢訂單 00039201
WHERE om.IKEY = :order_id
// 結果：找不到資料
```

**診斷過程**：
```sql
SELECT IKEY, LENGTH(IKEY), DUMP(IKEY, 16)
FROM GDWUUKT.ORDER_MN 
WHERE ROWNUM = 1;

-- 結果：
-- IKEY: 00039201
-- LENGTH: 10
-- DUMP: Typ=96 Len=10: 30,30,30,33,39,32,30,31,20,20
--                                                ^^^^
--                                        兩個空格（20,20）
```

**關鍵發現 #5**：IKEY 是 `CHAR(10)` 固定長度字段，實際值為 `'00039201  '`（後面補空格）

**解決方案**：使用 TRIM 函數
```sql
WHERE TRIM(om.IKEY) = :order_id
```

### 4.2 中文字符集支持問題

**問題現象**：
```
NJS-100: national character set id 871 is not supported by node-oracledb in Thin mode
```

**診斷**：
- Oracle 使用中文字符集（可能是 GBK 或 ZHS16GBK）
- oracledb Thin 模式不支持該字符集

**關鍵發現 #6**：需要使用 Thick 模式

**解決方案**：
```javascript
// 初始化 Oracle Client (Thick 模式)
oracledb.initOracleClient({ 
  libDir: 'D:\\app\\product\\12.2.0\\dbhome_1\\bin' 
});
```

---

## ✅ 階段五：成功測試（10分鐘）

### 5.1 查詢實際訂單

**測試訂單**：00039201

**查詢結果**：
```json
{
  "訂單編號": "00039201",
  "訂房人": "booking",
  "聯絡電話": "8862035640799",
  "入住日期": "2020-06-13",
  "退房日期": "2020-06-14",
  "住宿天數": 1,
  "訂單狀態": "O",
  "房型": "ST (標準房)",
  "房間數": 1,
  "成人數": 3,
  "兒童數": 0
}
```

**驗證項目**：
- ✅ 可以查詢訂單主檔
- ✅ 可以取得訂房人姓名
- ✅ 可以取得入住/退房日期
- ✅ 可以查詢房型資料
- ✅ 中文顯示正常

---

## 🔑 關鍵配置總結

### 最終配置資訊

```env
# 數據庫連接
DB_USER=pms_api
DB_PASSWORD=api123456
DB_CONNECT_STRING=localhost:1521/gdwuukt

# Oracle Client 路徑（Windows Server）
ORACLE_CLIENT_LIB_DIR=D:\\app\\product\\12.2.0\\dbhome_1\\bin

# Schema
SCHEMA=GDWUUKT
```

### 重要發現匯總

| # | 發現內容 | 重要性 |
|---|---------|--------|
| 1 | Mac 無法使用 Windows OS 驗證 | 🔴 高 |
| 2 | Oracle Client ≠ Oracle Database Server | 🔴 高 |
| 3 | Oracle 在 D 盤而非 C 盤 | 🔴 高 |
| 4 | GDWUUKT 才是正式環境 | 🔴 高 |
| 5 | IKEY 是 CHAR(10) 有尾隨空格 | 🟡 中 |
| 6 | 需要 Thick 模式支持中文 | 🔴 高 |

---

## 📝 最佳實踐建議

### 1. 查詢時必須使用 TRIM

```sql
-- ❌ 錯誤
WHERE om.IKEY = :order_id

-- ✅ 正確
WHERE TRIM(om.IKEY) = :order_id
```

### 2. 必須初始化 Thick 模式

```javascript
// 專案初始化時執行一次
try {
  oracledb.initOracleClient({ 
    libDir: process.env.ORACLE_CLIENT_LIB_DIR 
  });
} catch (err) {
  console.error('Oracle Client 初始化失敗：', err.message);
}
```

### 3. 使用連接池而非單一連接

```javascript
// ✅ 推薦：連接池
const pool = await oracledb.createPool({
  user: 'pms_api',
  password: 'api123456',
  connectString: 'localhost:1521/gdwuukt',
  poolMin: 2,
  poolMax: 10
});

// ❌ 不推薦：單一連接
const connection = await oracledb.getConnection({...});
```

### 4. Schema 明確指定

```sql
-- ✅ 明確指定 schema
SELECT * FROM GDWUUKT.ORDER_MN

-- ❌ 依賴默認 schema
SELECT * FROM ORDER_MN
```

---

## 🔍 德安 PMS 數據庫結構

### 資料庫環境分類

1. **GDWUUKT** - 正式環境
   - 訂單數量：1566 筆
   - 用途：龜地灣旅棧實際營運資料
   - 資料新鮮度：即時

2. **TEST** - 測試環境
   - 訂單數量：極少或無資料
   - 用途：測試用（但實際上沒在用）
   - 資料新鮮度：舊資料（2019年）

3. **DEMO** - 示範環境
   - 訂單數量：171 筆
   - 用途：德安資訊示範資料
   - 資料新鮮度：示範用假資料

### 主要資料表

| 資料表 | 用途 | 重要字段 |
|--------|------|---------|
| ORDER_MN | 訂單主檔 | IKEY, CUST_NAM, CONTACT1_RMK, CI_DAT, CO_DAT |
| ORDER_DT | 訂單明細 | IKEY, ROOM_COD, ORDER_QNT, ADULT_QNT |
| ROOM_RF | 房型主檔 | ROOM_TYP, ROOM_NAM, ROOM_QNT |

### 訂單狀態代碼

| 代碼 | 說明 |
|------|------|
| O | 已確認 |
| R | 預約中 |
| C | 已取消 |
| I | 已入住 |
| D | 已退房 |

---

## 🛠️ 故障排除指南

### 問題 1：ORA-12560

**症狀**：TNS: protocol adapter error

**可能原因**：
1. ORACLE_SID 未設定
2. Oracle 服務未啟動
3. ORACLE_HOME 路徑錯誤

**解決方案**：
```powershell
# 設定環境變數
$env:ORACLE_SID = "gdwuukt"
$env:ORACLE_HOME = "d:\app\product\12.2.0\dbhome_1"

# 檢查服務
Get-Service | Where-Object {$_.Name -like "*Oracle*"}

# 啟動服務（如需要）
net start OracleServiceGDWUUKT
```

### 問題 2：ORA-01017

**症狀**：使用者名稱/密碼無效

**可能原因**：
1. 帳號密碼錯誤
2. OS 驗證未生效
3. 帳號未創建

**解決方案**：
- 使用 sqlplus 測試：`sqlplus pms_api/api123456@localhost:1521/gdwuukt`
- 確認帳號存在：`SELECT username FROM dba_users WHERE username = 'PMS_API';`

### 問題 3：NJS-100

**症狀**：national character set id XXX is not supported

**原因**：Thin 模式不支持該字符集

**解決方案**：
```javascript
oracledb.initOracleClient({ 
  libDir: 'D:\\app\\product\\12.2.0\\dbhome_1\\bin' 
});
```

---

## 📚 參考資料

### 內部文件
- [Oracle 連接步驟](oracle_connection_steps.md)
- [PMS API 規格](../pms_api_specification.md)
- [PMS 資料庫參考](../PMS-DATABASE-REFERENCE.md)

### 外部資源
- [node-oracledb 文檔](https://node-oracledb.readthedocs.io/)
- [Oracle 錯誤代碼查詢](https://docs.oracle.com/error-help/)

---

## ✍️ 文件維護

**創建日期**：2025-12-10  
**最後更新**：2025-12-10  
**維護者**：KTW Bot Team  
**版本**：1.0

**變更歷史**：
- 2025-12-10：初始版本，記錄完整訪問過程
