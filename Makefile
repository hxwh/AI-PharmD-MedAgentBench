.PHONY: help install dev test test-cov test-quick clean run run-purple run-purple-mock run-full-test docker-build docker-run

help:
	@echo "MedAgentBench Green Agent - Makefile commands:"
	@echo ""
	@echo "Installation:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Install with test dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make test-quick   - Run quick test script"
	@echo ""
	@echo "Running:"
	@echo "  make run          - Run green agent server"
	@echo "  make run-purple   - Run purple agent (Gemini + MCP)"
	@echo "  make run-purple-mock - Run mock purple agent (for testing)"
	@echo "  make run-full-test - Run full integration test"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean        - Clean build artifacts"

install:
	pip install -e .

dev:
	pip install -e ".[test]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-quick:
	./tests/test.sh

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python src/server.py

run-purple-mock:
	python examples/mock_purple_agent.py

run-purple:
	python -m src.purple.server

run-full-test:
	python tests/full_test.py

docker-build:
	docker build -f Dockerfile -t aipharmd-green:latest .

docker-run:
	docker run -p 9009:9009 --env-file .env aipharmd-green:latest
