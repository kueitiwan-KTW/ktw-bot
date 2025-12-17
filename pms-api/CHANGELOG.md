# PMS REST API - Changelog

> PMS 資料庫 API 服務的詳細變更記錄

---

## [1.7.0] - 2025-12-17

### ✨ 新功能：訂單狀態回寫

#### 1. Mismatch 狀態標記
**檔案**: `routes/bookings.js`

- **新增端點**: `PATCH /api/bookings/same-day/:order_id/mismatch` (L586-650)
- **功能**: 將 `same_day_bookings.json` 中的訂單狀態更新為 `mismatch`
- **用途**: 當 Admin Web 點擊「已 KEY」但自動比對失敗時呼叫
- **實作**:
  ```javascript
  // 讀取訂單 -> 找到對應 ID -> 更新 status = 'mismatch' -> 寫回檔案
  targetBooking.status = 'mismatch';
  await fs.promises.writeFile(itemPath, JSON.stringify(bookings, null, 2));
  ```

#### 2. Check-in 邏輯增強
**檔案**: `routes/bookings.js` (L542-610)

- **修改**: `checkin` 端點現在會先執行 PMS 電話比對
- **邏輯**: 
  - Admin Web 觸發 -> Backend API 驗證 -> 比對成功 -> 呼叫 PMS `/checkin`
  - 比對失敗 -> Backend API 呼叫 PMS `/mismatch`

### 📝 修改的文件
- `routes/bookings.js` (L542-610, L586-650) - 新增與修改 Check-in/Mismatch 邏輯

---

## [1.6.0] - 2025-12-11

### ✨ 新功能：Windows 服務支援

1. **服務管理腳本**
   - **檔案**: `manage-service.bat`
   - **功能**: 整合 Start/Stop/Restart/Status 功能的批次檔
   - **位置**: 專案根目錄

2. **安裝/移除腳本**
   - **檔案**: `install_service.js`, `uninstall_service.js`
   - **功能**: 使用 `node-windows` 將 API 註冊為 Windows 本地服務
   - **設定**: 自動處理連線重試與錯誤重啟

### 🐛 Bug 修復

1. **Oracle 連線超時 (ORA-12170)**
   - **檔案**: `.env`, `listener.ora` (Server Side)
   - **問題**: `ORACLE_HOME` 環境變數衝突與 SID 配置錯誤
   - **修復**: 修正環境變數並重啟監聽器

2. **防火牆阻擋**
   - **設定**: Windows Firewall
   - **修復**: 開放 Inbound Port 3000

---

## [1.0.0] - 2025-12-10

### 初始版本
- 建立 Oracle DB 連線池
- 訂單查詢 API (Search by name/phone)
- 房況查詢 API (Room availability)
- 訂單詳情 API
