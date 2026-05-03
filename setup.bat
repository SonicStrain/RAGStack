@echo off
REM ════════════════════════════════════════════════════════
REM  RAGStack — Windows one-click setup
REM  Double-click this file to install RAGStack.
REM ════════════════════════════════════════════════════════

title RAGStack Setup

echo.
echo  RAGStack Setup
echo  ══════════════════════════════════════════════
echo.

REM Use py launcher if available, fall back to python
where py >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON=py
) else (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON=python
    ) else (
        echo  ERROR: Python not found. Install Python 3.10+ from https://python.org
        pause
        exit /b 1
    )
)

echo  Using: %PYTHON%
echo.

%PYTHON% install.py %*

if %errorlevel% neq 0 (
    echo.
    echo  Setup encountered an error. See message above.
    pause
    exit /b %errorlevel%
)

echo.
echo  Press any key to close...
pause >nul
