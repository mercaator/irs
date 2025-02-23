@echo off

:: Install coverage if not already installed
pip install coverage

:: Run tests with coverage
python -m coverage run -m unittest discover -s tests

:: Generate coverage report
python -m coverage report

:: Generate HTML coverage report
python -m coverage html

echo Coverage report generated. Open htmlcov\index.html to view the report.
