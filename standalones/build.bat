@echo off
REM Build move_anomalie as a standalone executable for Windows.
REM Requires: pip install pyinstaller  (see requirements-build.txt)
REM
REM Output: dist\move_anomalie.exe

cd /d "%~dp0"

pyinstaller move_anomalie.spec ^
    --distpath dist ^
    --workpath build\work ^
    --noconfirm

if %errorlevel%==0 (
    echo.
    echo Build complete: dist\move_anomalie.exe
    echo Copy dist\move_anomalie.exe + anomalie.txt into the images folder and run it.
) else (
    echo.
    echo Build failed. Make sure pyinstaller is installed: pip install pyinstaller
)
pause
