.PHONY: help install dev test lint train serve api docker-build docker-up clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .
	python -m spacy download en_core_web_sm || true

dev:  ## Install development dependencies
	pip install -e ".[all]"
	python -m spacy download en_core_web_sm || true

test:  ## Run all tests with coverage
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

lint:  ## Run linter
	ruff check src/ tests/

format:  ## Auto-format code
	ruff format src/ tests/

train:  ## Run model training pipeline
	python training/train.py

serve:  ## Run Streamlit app locally
	streamlit run streamlit_app.py

api:  ## Run FastAPI server locally
	uvicorn src.api.app:app --reload --port 8000

docker-build:  ## Build Docker image
	docker-compose build

docker-up:  ## Start all services via Docker
	docker-compose up -d

docker-down:  ## Stop all Docker services
	docker-compose down

clean:  ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage dist/ build/ *.egg-info
