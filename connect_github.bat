@echo off
echo Connecting local repository to GitHub...

REM Add the remote repository (replace with your actual GitHub repo URL)
git remote add origin https://github.com/brucegifford/PuzPieceMaker.git

REM Push the code to GitHub
echo Pushing code to GitHub...
git branch -M main
git push -u origin main

echo.
echo Repository successfully connected to GitHub!
echo You can now view your project at: https://github.com/brucegifford/PuzPieceMaker
echo.
pause
