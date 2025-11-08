#!/bin/bash

# Run code quality checks
echo "Running flake8..."
flake8 app/ tests/

echo "Running mypy..."
mypy app/

echo "Checking import sorting..."
isort --check-only app/ tests/

echo "Checking code formatting..."
black --check app/ tests/

echo "Linting complete!"