@echo off
chcp 65001 >nul
set MYSQLD=C:\Users\13230\mysql8\mysql-8.0.46-winx64\bin\mysqld.exe
set MYINI=C:\Users\13230\mysql8\my.ini

if not exist "%MYSQLD%" (
  echo [ERROR] mysqld not found: %MYSQLD%
  pause
  exit /b 1
)

netstat -ano | findstr ":3306" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
  echo MySQL is already running on port 3306.
  pause
  exit /b 0
)

echo Starting MySQL 8.0 ...
start "MySQL 8.0" "%MYSQLD%" --defaults-file="%MYINI%" --console
timeout /t 4 >nul

netstat -ano | findstr ":3306" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
  echo MySQL started. The new window must stay open while you work.
) else (
  echo [WARN] Port 3306 not ready yet. Check the MySQL window for errors.
)
pause
