@echo off
chcp 65001
echo ================================================
echo   拼多多 AI 客服自动回复
echo   powered by DeepSeek
echo ================================================
echo.
cd /d "%~dp0"
python pdd_ai_kefu.py
pause
