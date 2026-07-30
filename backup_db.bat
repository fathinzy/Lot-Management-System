@echo off
REM ============================================================
REM Lot Management System - Daily Database Backup
REM
REM What this does: copies lot_management.db to a backup folder,
REM with today's date in the filename, so you keep a history of
REM daily backups instead of one file being silently overwritten.
REM
REM SETUP (for IT):
REM   1. Edit the two paths below (SOURCE_DB and BACKUP_DIR) to
REM      match where the app and your backup location actually are.
REM   2. Save this file somewhere permanent, e.g.
REM      C:\LotManagementSystem\backup_db.bat
REM   3. Open Windows Task Scheduler -> Create Basic Task.
REM        Name: "Lot Management DB Backup"
REM        Trigger: Daily, e.g. 6:00 PM (after the shift ends)
REM        Action: Start a program -> point it at this .bat file
REM   4. Right-click the task -> Run, once, to confirm it works
REM      before relying on the schedule.
REM ============================================================

set SOURCE_DB=C:\LotManagementSystem\lot_management.db
set BACKUP_DIR=D:\Backups\LotManagementSystem

REM Build a date stamp like 2026-08-01 regardless of Windows locale
for /f "tokens=1-3 delims=/- " %%a in ('wmic os get localdatetime ^| findstr /r "^[0-9]"') do set DTS=%%a
set YEAR=%DTS:~0,4%
set MONTH=%DTS:~4,2%
set DAY=%DTS:~6,2%
set STAMP=%YEAR%-%MONTH%-%DAY%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

if not exist "%SOURCE_DB%" (
    echo ERROR: Could not find %SOURCE_DB% - check the SOURCE_DB path in this script.
    exit /b 1
)

copy /Y "%SOURCE_DB%" "%BACKUP_DIR%\lot_management_%STAMP%.db"

if %ERRORLEVEL% EQU 0 (
    echo Backup successful: %BACKUP_DIR%\lot_management_%STAMP%.db
) else (
    echo ERROR: Backup failed. Check that %BACKUP_DIR% is accessible.
)

REM Optional: automatically delete backups older than 90 days.
REM Uncomment the line below once you've confirmed backups are working.
REM forfiles /p "%BACKUP_DIR%" /s /m *.db /d -90 /c "cmd /c del @path"
