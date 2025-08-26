#!/bin/bash

# Script to run all tests and quality checks

set -e  # Exit on any error

echo "Running all tests and quality checks..."

# Check if pdm is installed
if ! command -v pdm &> /dev/null
then
    echo "pdm could not be found, please install it first"
    exit 1
fi

# Install dependencies if not already installed
echo "Installing dependencies..."
pdm install -G test -G dev --no-self

# Run linting
echo "Running code linting..."
pdm run lint

# Run formatting check
echo "Running code formatting check..."
pdm run format --check

# Run type checking
echo "Running type checking..."
pdm run type-check

# Run security checks
echo "Running security checks..."
pdm run security

# Run tests
echo "Running tests..."
pdm run test

echo "All checks passed successfully!"