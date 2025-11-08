@echo off
REM Format code with black and isort

echo Formatting code with black...
black app\ tests\

echo Sorting imports with isort...
isort app\ tests\

echo Code formatting complete!