@echo off
chcp 65001 >nul
title 建立 AGY Token Monitor 桌面捷徑
echo ==================================================
echo  AGY Token Monitor - 一鍵建立桌面捷徑
echo ==================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] 桌面捷徑建立完成！
) else (
    echo.
    echo [ERROR] 建立捷徑時發生錯誤，請以系統管理員身分重試。
)

echo.
pause
