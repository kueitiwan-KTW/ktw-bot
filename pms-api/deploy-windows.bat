@echo off
REM ========================================
REM PMS API - Windows Server 部署腳本
REM ========================================

echo.
echo ========================================
echo PMS API 部署程式
echo ========================================
echo.

REM 檢查 Node.js
echo [1/6] 檢查 Node.js...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 未安裝 Node.js
    echo.
    echo 請先安裝 Node.js v20.10.0
    pause
    exit /b 1
)

node --version
npm --version
echo ✅ Node.js 已安裝
echo.

REM 切換到專案目錄
echo [2/6] 切換到專案目錄...
cd /d "C:\KTW-bot\pms-api"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 找不到專案目錄 C:\KTW-bot\pms-api
    echo 請先將檔案複製到此目錄
    pause
    exit /b 1
)
echo ✅ 目錄正確
echo.

REM 檢查檔案
echo [3/6] 檢查專案檔案...
if not exist "package.json" (
    echo ❌ 找不到 package.json
    pause
    exit /b 1
)
if not exist "server.js" (
    echo ❌ 找不到 server.js
    pause
    exit /b 1
)
echo ✅ 檔案完整
echo.

REM 安裝依賴
echo [4/6] 安裝 npm 套件...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 安裝失敗
    pause
    exit /b 1
)
echo ✅ 套件安裝完成
echo.

REM 配置環境變數
echo [5/6] 配置環境變數...
if not exist ".env" (
    copy .env.example .env
    echo ✅ 已建立 .env 檔案
    echo.
    echo ⚠️  請編輯 .env 檔案確認資料庫連線設定
    echo.
    notepad .env
) else (
    echo ℹ️  .env 檔案已存在
)
echo.

REM 測試啟動
echo [6/6] 測試 API...
echo.
echo 正在啟動 PMS API 伺服器...
echo 請稍候 5 秒後檢查是否成功啟動
echo.
echo 如果成功，您將看到：
echo 🚀 PMS API 伺服器已啟動
echo 📡 監聽端口: 3000
echo.
echo 按 Ctrl+C 可停止伺服器
echo.
timeout /t 3 /nobreak >nul

npm start

REM 如果執行到這裡，表示伺服器已停止
echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 📝 使用說明：
echo.
echo 啟動 API：
echo    cd C:\KTW-bot\pms-api
echo    npm start
echo.
echo 測試 API：
echo    開啟瀏覽器：http://localhost:3000/api/health
echo.
pause
