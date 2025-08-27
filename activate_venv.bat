@echo off
echo Activating virtual environment for Puzzle Grid Viewer...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup_venv.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Virtual environment activated!
echo You can now run Python commands in the virtual environment.
echo.
echo To run the application:
echo   python puzzle_grid_viewer.py
echo.
echo To deactivate the environment later, type:
echo   deactivate
echo.
call venv\Scripts\activate.bat
