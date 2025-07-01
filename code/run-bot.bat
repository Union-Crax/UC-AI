@echo off
REM Start Ollama server if not running (Windows)
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo Starting Ollama server...
    start "Ollama" /MIN ollama serve
    timeout /t 5 >nul
)

cd /d %~dp0bot
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
