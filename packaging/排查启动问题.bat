@echo off
cd /d "%~dp0"
"%~dp0runtime\python.exe" -m film_contact_sheet
echo.
echo 如果上面有报错，请把这段文字留存。
pause
