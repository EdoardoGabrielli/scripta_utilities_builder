@echo off
REM Smoke test for the Windows executable.
REM Usage: smoke_test.bat <path-to-exe>
REM Example: smoke_test.bat dist\move_anomalie.exe

if "%~1"=="" (
    echo Usage: smoke_test.bat ^<path-to-exe^>
    exit /b 1
)
"%~1" --smoke
