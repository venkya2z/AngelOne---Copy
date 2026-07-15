@echo off
TITLE Angel One Trading Bot Launcher
echo ===================================================
echo    Angel One - Trading Strategy Engine
echo    Starting All Services...
echo ===================================================
echo.

:: Verify correct directory
if not exist "backend\main.py" (
    echo ERROR: backend\main.py not found!
    echo Please run this script from the AngelOne root directory.
    pause
    exit /b 1
)

:: 1. Start Backend (ALWAYS main.py)
echo [1/2] Launching Backend Service (main.py)...
start "AngelOne Backend" cmd /k "chcp 65001 >nul && cd backend && python main.py"


:: Wait for backend to initialize
timeout /t 3 /nobreak >nul

:: 2. Start Frontend (Next.js Dashboard)
echo [2/2] Launching Frontend Dashboard...
start "AngelOne UI" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo    All Services Started Successfully!
echo    Backend API: http://127.0.0.1:8000
echo    Frontend UI: http://localhost:3000
echo ===================================================
echo.
echo IMPORTANT: Always verify the backend terminal shows:
echo [Main] Login Successful
echo.

:: 3. Open Browser
echo Opening Dashboard in Browser in 7 seconds...
timeout /t 7 /nobreak
start http://localhost:3000

pause
