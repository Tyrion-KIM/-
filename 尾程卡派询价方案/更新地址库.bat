@echo off
chcp 65001 >nul
cd /d "%~dp0"
python extract_address_book.py
python extract_price_book.py
echo.
echo 已同步更新 address_book.js（V1 地址库）与 price_book.js（V2 报价库）
pause
