@echo off
python importer.py
if errorlevel 1 (
    echo.
    echo Something went wrong. See the message above.
)
pause
