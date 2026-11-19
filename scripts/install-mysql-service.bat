@echo off
chcp 65001 >nul
set MYSQLD=C:\Users\13230\mysql8\mysql-8.0.46-winx64\bin\mysqld.exe
set MYINI=C:\Users\13230\mysql8\my.ini

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] Please right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)

sc query MySQL80 >nul 2>&1
if %errorlevel% equ 0 (
  echo Service MySQL80 already exists. Starting it ...
) else (
  echo Creating service MySQL80 ...
  sc create MySQL80 binPath= "%MYSQLD% --defaults-file=%MYINI%" start= auto
  if %errorlevel% neq 0 (
    echo [ERROR] Failed to create service.
    pause
    exit /b 1
  )
)

sc start MySQL80
timeout /t 5 >nul
netstat -ano | findstr ":3306" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
  echo MySQL service is running. It will start automatically on boot.
) else (
  echo [WARN] Service created but port 3306 is not listening yet.
  echo Check Windows Services or run: sc query MySQL80
)
pause
