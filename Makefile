# FinPulse Makefile

.PHONY: help setup run-cli app test clean install-deps

# Default target
help:
	@echo "FinPulse - AI-powered financial report generator"
	@echo ""
	@echo "Available commands:"
	@echo "  setup       - Set up the development environment"
	@echo "  run-cli     - Run CLI with example (AAPL 10-Q)"
	@echo "  app         - Launch Streamlit web interface"
	@echo "  test        - Run tests"
	@echo "  clean       - Clean cache and temporary files"
	@echo "  install-deps - Install Python dependencies"
	@echo ""

# Set up development environment
setup: install-deps
	@echo "Setting up FinPulse environment..."
	@mkdir -p data/cache
	@echo "Environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env and add your GEMINI_API_KEY"
	@echo "2. Run 'make run-cli' to test the CLI"
	@echo "3. Run 'make app' to launch the web interface"

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Dependencies installed!"

# Run CLI with example
run-cli:
	@echo "Running FinPulse CLI with AAPL 10-Q example..."
	@if [ ! -f .env ]; then \
		echo "Warning: .env file not found. Using default settings."; \
	fi
	python3 -m finpulse --ticker AAPL --scope 10Q

# Launch Gradio web interface
app:
	@echo "Launching FinPulse web interface..."
	@if [ ! -f .env ]; then \
		echo "Warning: .env file not found. Using default settings."; \
	fi
	python3 app/gradio_app.py

# Run tests
test:
	@echo "Running FinPulse tests..."
	python3 -m pytest tests/ -v

# Clean cache and temporary files
clean:
	@echo "Cleaning cache and temporary files..."
	rm -rf data/cache/*
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf src/finpulse/__pycache__/
	rm -rf src/finpulse/*/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	rm -rf finpulse.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete!"

# Development helpers
dev-setup: setup
	@echo "Setting up development environment..."
	pip install -e .
	@echo "Development setup complete!"

# Quick test without full setup
quick-test:
	@echo "Running quick test..."
	python3 -c "import sys; sys.path.insert(0, 'src'); from finpulse.ingest.edgar import EdgarClient; print(' Import test passed!')"
