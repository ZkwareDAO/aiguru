#!/bin/bash

# Run tests with coverage
echo "Running tests with coverage..."
pytest --cov=app --cov-report=term-missing --cov-report=html

echo "Tests complete! Coverage report available in htmlcov/"