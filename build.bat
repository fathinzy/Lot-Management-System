@echo off
REM ==========================================================================
REM  Build the Lot Management System into a double-clickable Windows .exe.
REM
REM  Run this ONCE on a build machine that has Python installed (it does NOT
REM  need to be an OQC laptop). Just double-click build.bat, or run it from a
REM  command prompt in this folder.
REM
REM  When it finishes, the finished app is in:
REM      dist\LotManagementSystem\
REM  Copy that whole folder to each OQC laptop. They double-click
REM  LotManagementSystem.exe inside it - no Python needed on their machine.
REM ==========================================================================

echo.
echo ==== Lot Management System - build .exe ====
echo.

REM Move to the folder this script lives in, so it works no matter where
REM it's launched from.
cd /d "%~dp0"

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found on this machine.
    echo Install Python 3.9+ from https://www.python.org/downloads/ and
    echo tick "Add python.exe to PATH" during install, then run build.bat again.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing the app's runtime requirements...
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [3/4] Installing the build tool (PyInstaller)...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo.
echo [4/4] Building the .exe (this can take a couple of minutes)...
python -m PyInstaller --noconfirm --clean LotManagementSystem.spec
if errorlevel 1 goto :fail

echo.
echo ==========================================================================
echo  DONE.
echo  Your app is here:  dist\LotManagementSystem\
echo  Give the OQC user the whole "LotManagementSystem" folder and tell them
echo  to double-click LotManagementSystem.exe inside it.
echo ==========================================================================
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Scroll up to see the first red/error line - that's the cause.
echo.
pause
exit /b 1
