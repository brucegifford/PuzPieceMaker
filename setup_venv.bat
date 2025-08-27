@echo off
echo Setting up virtual environment for Puzzle Grid Viewer...

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Check if virtual environment was created successfully
if not exist "venv\Scripts\activate.bat" (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

echo Virtual environment created successfully!

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

echo.
echo Setup complete! Virtual environment is ready.
echo.
echo To activate the environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo To run the application:
echo   python puzzle_grid_viewer.py
echo.
pause
