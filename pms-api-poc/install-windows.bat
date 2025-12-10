@echo off
REM ========================================
REM PMS API POC - Windows Server 安裝腳本
REM ========================================

echo.
echo ========================================
echo PMS API POC 安裝程式
echo ========================================
echo.

REM 檢查 Node.js
echo [1/5] 檢查 Node.js...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 未安裝 Node.js
    echo.
    echo 請先安裝 Node.js:
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)

node --version
npm --version
echo ✅ Node.js 已安裝
echo.

REM 建立目錄
echo [2/5] 建立目錄...
if not exist "C:\KTW-bot\pms-api-poc" (
    mkdir "C:\KTW-bot\pms-api-poc"
    echo ✅ 目錄已建立: C:\KTW-bot\pms-api-poc
) else (
    echo ℹ️  目錄已存在
)
echo.

REM 複製檔案提示
echo [3/5] 複製專案檔案...
echo.
echo ⚠️  請手動將以下檔案複製到 C:\KTW-bot\pms-api-poc:
echo    - package.json
echo    - test-connection.js
echo    - test-query.js
echo    - .env.example
echo.
echo 複製完成後按任意鍵繼續...
pause >nul
echo.

REM 切換到專案目錄
cd /d "C:\KTW-bot\pms-api-poc"

REM 檢查檔案
if not exist "package.json" (
    echo ❌ 找不到 package.json
    echo 請確認檔案已正確複製
    pause
    exit /b 1
)

REM 安裝依賴
echo [4/5] 安裝 npm 套件...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 安裝失敗
    pause
    exit /b 1
)
echo ✅ 套件安裝完成
echo.

REM 配置環境變數
echo [5/5] 配置環境變數...
if not exist ".env" (
    copy .env.example .env
    echo ✅ 已建立 .env 檔案
    echo.
    echo ⚠️  請編輯 .env 檔案:
    echo    設定 DB_CONNECT_STRING=localhost:1521/gdwuukt
    echo.
    notepad .env
) else (
    echo ℹ️  .env 檔案已存在
)
echo.

REM 完成
echo ========================================
echo ✅ 安裝完成！
echo ========================================
echo.
echo 📝 下一步:
echo    1. 確認 .env 檔案已正確設定
echo    2. 執行: npm test (測試連線)
echo    3. 執行: npm run test-query (測試查詢)
echo.
pause
