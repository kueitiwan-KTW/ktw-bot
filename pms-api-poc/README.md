# Oracle PMS API POC 測試程式

> **重要**: 此 POC 已驗證成功！請參考 `/pms-api/` 目錄中的完整 REST API 實現。

這是一個概念驗證（POC）專案，用於測試 Oracle PMS 資料庫的連接與查詢功能。

## ✅ 驗證結果

**日期**: 2025-12-10  
**狀態**: ✅ 成功

- ✅ Oracle 連接測試通過
- ✅ 訂單查詢測試通過
- ✅ 中文字符集支持
- ✅ 真實訂單資料查詢成功

## 關鍵發現

1. **正確的 Schema**: `GDWUUKT`（非 TEST）
2. **Oracle 位置**: D:\app\product\12.2.0\dbhome_1（非 C 盤）
3. **字符集**: 需使用 Thick 模式支持中文
4. **IKEY 字段**: CHAR(10) 固定長度，需使用 TRIM()

詳細過程請參考：[docs/oracle/oracle_access_journey.md](../docs/oracle/oracle_access_journey.md)

## 環境需求

- Node.js v20.10.0 或以上
- Oracle Database 12c
- Windows Server（需訪問 Oracle Client）
- pms_api 帳號（已創建並授權）

## 安裝步驟

### 1. 安裝依賴

```bash
npm install
```

### 2. 配置環境變數

複製 `.env.example` 為 `.env`：

```bash
copy .env.example .env
```nano .env  # 編輯檔案，填入 DB_PASSWORD
```

### 3. 執行測試

#### 測試 1：資料庫連線
```bash
npm test
```

**預期結果**：
- ✅ 連線成功
- ✅ 顯示 Oracle 版本

#### 測試 2：查詢訂單資料
```bash
npm run test-query
```

**預期結果**：
- ✅ 查到訂單資料
- ✅ 顯示訂房人姓名
- ✅ 顯示入住/退房日期
- ✅ 顯示房型資訊

## 📊 測試項目清單

- [ ] Oracle 資料庫連線成功
- [ ] 可查詢訂單主檔（ORDER_MN）
- [ ] 可查詢訂單明細（ORDER_DT）
- [ ] 可查詢房型資料（ROOM_RF）
- [ ] 資料格式符合 API 設計
- [ ] 回應時間 < 500ms

## ⚠️ 可能遇到的問題

### 問題 1：連線失敗
```
Error: ORA-01017: invalid username/password
```
**解決方法**：檢查 `.env` 中的 `DB_PASSWORD` 是否正確

### 問題 2：找不到資料表
```
Error: ORA-00942: table or view does not exist
```
**解決方法**：確認 Schema 名稱是否為 `TEST`

### 問題 3：找不到訂單
```
❌ 找不到訂單編號 00150501
```
**解決方法**：修改 `.env` 中的 `TEST_ORDER_ID` 為實際存在的訂單號

## 📝 下一步

當所有測試都通過後：
1. ✅ 建立完整的 Express API 服務
2. ✅ 實作 5 個 REST API 端點
3. ✅ 整合到 LINE BOT

## 🔗 相關文件

- [PMS API 規格](../docs/pms_api_specification.md)
- [資料庫結構](../docs/pms_database_structure.md)
