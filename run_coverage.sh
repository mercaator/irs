#!/bin/sh

# Install coverage if not already installed
pip install coverage

# Run tests with coverage
coverage run -m unittest discover -s tests

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html

echo "Coverage report generated. Open htmlcov/index.html to view the report."
