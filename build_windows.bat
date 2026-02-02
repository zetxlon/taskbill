@echo off
setlocal

REM Create venv
python -m venv .venv
call .venv\Scripts\activate

REM Install deps
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM Build onefile exe
pyinstaller --noconfirm --onefile --windowed taskbill.py

echo.
echo Build finished. Look in .\dist\taskbill.exe
pause
