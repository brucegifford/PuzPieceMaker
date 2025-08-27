@echo off
echo Updating pip in virtual environment...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup_venv.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Update pip
echo Updating pip to latest version...
python -m pip install --upgrade pip

echo.
echo Pip has been updated successfully!
echo Current pip version:
pip --version
echo.
pause
