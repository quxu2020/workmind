@echo off
chcp 65001 > nul
echo 正在启动热点采集工具Web版...
echo.
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" web.py
pause
