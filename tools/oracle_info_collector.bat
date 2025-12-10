@echo off
chcp 65001 >nul
echo Starting Oracle information collection...
echo.

cd /d %~dp0
set OUTPUT_FILE=%~dp0oracle_info_result.txt

echo Oracle Database Information Collection > "%OUTPUT_FILE%"
echo ======================================== >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"

echo [1] Checking E:\app\oradata...
echo === 1. E:\app\oradata === >> "%OUTPUT_FILE%"
if exist "E:\app\oradata" (
    dir "E:\app\oradata" >> "%OUTPUT_FILE%" 2>&1
) else (
    echo Directory not found >> "%OUTPUT_FILE%"
)
echo. >> "%OUTPUT_FILE%"

echo [2] Checking TNS configuration...
echo === 2. TNS Configuration === >> "%OUTPUT_FILE%"
if exist "C:\app\product\12.2.0\client_1\network\admin\tnsnames.ora" (
    type "C:\app\product\12.2.0\client_1\network\admin\tnsnames.ora" >> "%OUTPUT_FILE%" 2>&1
) else (
    echo File not found >> "%OUTPUT_FILE%"
)
echo. >> "%OUTPUT_FILE%"

echo [3] Checking E:\app directories...
echo === 3. E:\app Directories === >> "%OUTPUT_FILE%"
if exist "E:\app" (
    dir "E:\app" /ad >> "%OUTPUT_FILE%" 2>&1
) else (
    echo Directory not found >> "%OUTPUT_FILE%"
)
echo. >> "%OUTPUT_FILE%"

echo [4] Checking environment variables...
echo === 4. Environment Variables === >> "%OUTPUT_FILE%"
echo ORACLE_HOME=%ORACLE_HOME% >> "%OUTPUT_FILE%"
echo ORACLE_SID=%ORACLE_SID% >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"

echo.
echo Done! Results saved to:
echo %OUTPUT_FILE%
echo.
echo Please open this file and copy all content.
echo.
echo Press any key to open the result file...
pause >nul
notepad "%OUTPUT_FILE%"
