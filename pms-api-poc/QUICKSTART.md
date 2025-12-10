# 快速部署檢查表

## 準備工作
- [ ] 連線到 Windows Server (192.168.8.3)
- [ ] 確認 Oracle 服務正在運行

## 安裝 Node.js
```powershell
# 1. 下載並安裝 Node.js v20.10.0 LTS
# https://nodejs.org/

# 2. 驗證安裝
node --version
npm --version
```

## 部署 POC 測試
```powershell
# 1. 建立目錄
cd C:\
mkdir KTW-bot\pms-api-poc
cd KTW-bot\pms-api-poc

# 2. 複製檔案（從您的 Mac）
# - package.json
# - test-connection.js
# - test-query.js
# - .env.example

# 3. 安裝依賴
npm install

# 4. 配置環境
copy .env.example .env
notepad .env
# 設定：DB_CONNECT_STRING=localhost:1521/gdwuukt

# 5. 執行測試
npm test
npm run test-query
```

## 測試成功標準
✅ 連線測試顯示：「連線成功」
✅ 訂單查詢顯示：訂房人、日期、房型資料

## 下一步
測試成功後回報，我會協助建立完整的 REST API 服務。
