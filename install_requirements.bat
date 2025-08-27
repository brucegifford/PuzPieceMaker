@echo off
echo Installing requirements for Puzzle Grid Viewer...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup_venv.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo Error: requirements.txt not found!
    echo Make sure you're running this from the project directory.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements from requirements.txt...
pip install -r requirements.txt

echo.
echo Requirements installed successfully!
echo.
echo You can now run the application with:
echo   python puzzle_grid_viewer.py
echo.
pause
