# Makefile for Blackcore Minimal Module Testing

.PHONY: help test test-unit test-integration test-coverage lint format clean

help:
	@echo "Available commands:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make test-performance - Run performance tests"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean test artifacts"

# Run all tests
test:
	pytest tests/ -v

# Run unit tests only
test-unit:
	pytest tests/unit/ -v

# Run integration tests only
test-integration:
	pytest tests/integration/ -v

# Run tests with coverage
test-coverage:
	pytest tests/ -v --cov=blackcore.minimal --cov-report=html --cov-report=term-missing

# Run performance tests
test-performance:
	pytest tests/integration/test_performance.py -v

# Run specific test file
test-file:
	@echo "Usage: make test-file FILE=tests/unit/test_config.py"
	pytest $(FILE) -v

# Run linting
lint:
	ruff check .
	ruff format --check .

# Format code
format:
	ruff format .
	ruff check --fix .

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .test_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Watch tests (requires pytest-watch)
watch:
	ptw tests/ -- -v

# Run tests in parallel (requires pytest-xdist)
test-parallel:
	pytest tests/ -v -n auto

# Generate test report
test-report:
	pytest tests/ --html=report.html --self-contained-html -v

# Check test markers
test-markers:
	pytest --markers

# Dry run - collect tests without running
test-collect:
	pytest tests/ --collect-only