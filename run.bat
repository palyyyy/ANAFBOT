@echo off
title ANAF e-Factura Downloader
echo ========================================================
echo       ANAF e-Factura Downloader Launcher
echo ========================================================
echo.
echo Checking Python libraries...
python -c "import fastapi, uvicorn, requests, cryptography" >nul 2>nul
if %errorlevel% neq 0 (
    echo Dependencies not found. Installing required libraries...
    python -m pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to install dependencies automatically.
        echo Please ensure you are connected to the internet and python is in your PATH.
        echo.
        pause
        exit /b
    )
)

echo Starting local web server...
python "%~dp0main.py"
pause
