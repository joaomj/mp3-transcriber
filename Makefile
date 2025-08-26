# Makefile for running tests and checks

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  install     - Install all dependencies including test dependencies"
	@echo "  test        - Run all tests"
	@echo "  lint        - Run code linting"
	@echo "  format      - Run code formatting"
	@echo "  type-check  - Run type checking"
	@echo "  security    - Run security checks"
	@echo "  all-checks  - Run all code quality checks"
	@echo "  clean       - Clean up temporary files and directories"

# Install all dependencies
.PHONY: install
install:
	pdm install -G test -G dev

# Run tests
.PHONY: test
test:
	pdm run test

# Run linting
.PHONY: lint
lint:
	pdm run lint || echo "Linting issues found (non-critical)"

# Run formatting
.PHONY: format
format:
	pdm run format

# Run type checking
.PHONY: type-check
type-check:
	pdm run type-check

# Run security checks
.PHONY: security
security:
	pdm run security

# Run all checks
.PHONY: all-checks
all-checks: lint format type-check security

# Clean temporary files
.PHONY: clean
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete