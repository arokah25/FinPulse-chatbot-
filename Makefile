# FinPulse Makefile

.PHONY: help setup run-cli app test clean install-deps

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


# Launch Gradio web interface
app:
	@echo "Launching FinPulse web interface..."
	@if [ ! -f .env ]; then \
		echo "Warning: .env file not found. Using default settings."; \
	fi
	python3 app/gradio_app.py

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
