@echo off
REM Validate configuration for all environments

echo Validating configuration...
python scripts\validate_config.py

if %ERRORLEVEL% NEQ 0 (
    echo Configuration validation failed!
    exit /b 1
)

echo Configuration validation passed!