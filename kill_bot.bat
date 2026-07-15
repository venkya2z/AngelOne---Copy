@echo off
TITLE Kill Angel Bot Processes
echo ===================================================
echo    Killing Angel One Trading Bot Processes...
echo ===================================================
echo.

:: Kill ONLY AngelOne Backend (by window title)
echo [1/2] Stopping AngelOne Backend...
taskkill /FI "WindowTitle eq AngelOne Backend*" /F /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     AngelOne Backend terminated.
) else (
    echo     AngelOne Backend not running.
)

:: Kill ONLY AngelOne Frontend (by window title)
echo [2/3] Stopping AngelOne Frontend...
taskkill /FI "WindowTitle eq AngelOne UI*" /F /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     AngelOne Frontend terminated.
) else (
    echo     AngelOne Frontend not running.
)

:: Clear Next.js Lock File (Safe to keep)
if exist frontend\.next\dev\lock (
    echo     Removing stale lock file...
    del frontend\.next\dev\lock
)

:: Kill ONLY AngelOne Backend (by window title)
echo [3/3] Stopping AngelOne Backend...
taskkill /FI "WindowTitle eq AngelOne Backend*" /F /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     AngelOne Backend terminated.
) else (
    echo     AngelOne Backend not running.
)

echo.
echo ===================================================
echo    AngelOne bot processes stopped.
echo    Other Python/Node processes unaffected.
echo ===================================================
echo.
pause
