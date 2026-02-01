.PHONY: lint format test install

install:
	pip install ruff pytest pytest-cov
	pip install -r requirements.txt

lint:
	ruff check .

format:
	ruff format .

test:
	pytest tests/ -v --cov=src
