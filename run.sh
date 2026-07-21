#!/bin/bash
echo "========================================================"
echo "   ANAF e-Factura Downloader Launcher (macOS/Linux)"
echo "========================================================"
echo ""

# Find correct python command (python3 is standard on macOS)
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python is not installed or not in your PATH."
        echo "Please install Python from https://www.python.org/downloads/"
        exit 1
    fi
fi

echo "Checking Python libraries..."
$PYTHON_CMD -c "import fastapi, uvicorn, requests, cryptography" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Dependencies not found. Installing required libraries..."
    $PYTHON_CMD -m pip install -r "$(dirname "$0")/requirements.txt"
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Failed to install dependencies automatically."
        echo "Please ensure you are connected to the internet."
        echo ""
        exit 1
    fi
fi

echo "Starting local web server..."
$PYTHON_CMD "$(dirname "$0")/main.py"
