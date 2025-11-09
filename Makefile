# PAN-OS Agent Makefile
# Handles virtual environment, dependencies, evaluation, and dataset management

.PHONY: help venv install evaluate evaluate-ci dataset-create dataset-template dataset-list dataset-delete clean test lint format check

# Configuration
PYTHON_VERSION ?= 3.11
VENV := .venv
UV := uv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UV_PYTHON := $(shell $(UV) python find $(PYTHON_VERSION) 2>/dev/null || echo python3)

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)PAN-OS Agent Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make venv          - Create virtual environment"
	@echo "  make install       - Install dependencies"
	@echo ""
	@echo "$(GREEN)Evaluation:$(NC)"
	@echo "  make evaluate      - Run evaluation (local, saves results)"
	@echo "  make evaluate-ci   - Run evaluation (CI, fails if <90% success)"
	@echo ""
	@echo "$(GREEN)Dataset Management:$(NC)"
	@echo "  make dataset-create DATASET=name - Create LangSmith dataset (shows template guide)"
	@echo "  make dataset-template            - Show dataset template guide"
	@echo "  make dataset-list                - List LangSmith datasets"
	@echo "  make dataset-delete DATASET=name - Delete LangSmith dataset"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make check        - Run all checks (lint + format + test)"
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@echo "  make clean        - Remove virtual environment and cache files"
	@echo ""

# Check if uv is installed
check-uv:
	@if ! command -v $(UV) >/dev/null 2>&1; then \
		echo "$(RED)Error: $(UV) is not installed$(NC)"; \
		echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	fi

# Create virtual environment if it doesn't exist
venv: check-uv
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(BLUE)Creating virtual environment...$(NC)"; \
		$(UV) venv --python $(PYTHON_VERSION) $(VENV); \
		echo "$(GREEN)✓ Virtual environment created$(NC)"; \
	else \
		echo "$(GREEN)✓ Virtual environment already exists$(NC)"; \
	fi

# Install dependencies
install: venv check-uv
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@$(UV) pip install -e ".[dev]"
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

# Ensure virtual environment and dependencies are ready
ensure-setup: install
	@# Marker target - dependencies will be checked by install

# Run evaluation (local)
evaluate: ensure-setup
	@echo "$(BLUE)Running evaluation suite...$(NC)"
	@$(PYTHON) scripts/evaluate.py --mode both --save-results
	@echo "$(GREEN)✓ Evaluation complete$(NC)"
	@echo "$(YELLOW)Results saved to evaluation_results/$(NC)"

# Run evaluation (CI - fails if success rate < 90%)
evaluate-ci: ensure-setup
	@echo "$(BLUE)Running evaluation suite (CI mode)...$(NC)"
	@$(PYTHON) scripts/evaluate.py --mode both --save-results || exit 1
	@echo "$(BLUE)Checking success rates...$(NC)"
	@$(PYTHON) -c " \
		import json; \
		import glob; \
		from pathlib import Path; \
		results = list(Path('evaluation_results').glob('eval_*.json')); \
		if not results: \
			print('$(RED)ERROR: No evaluation results found$(NC)'); \
			exit(1); \
		all_pass = True; \
		for r in results: \
			with open(r) as f: \
				data = json.load(f); \
				sr = data['metrics']['success_rate']; \
				mode = data['mode']; \
				if sr < 0.90: \
					print(f'$(RED)FAIL: {r.name} ({mode}) success rate {sr:.1%} < 90%$(NC)'); \
					all_pass = False; \
				else: \
					print(f'$(GREEN)PASS: {r.name} ({mode}) success rate {sr:.1%}$(NC)'); \
		if not all_pass: \
			print('$(RED)ERROR: One or more evaluations failed threshold$(NC)'); \
			exit(1); \
		print('$(GREEN)✓ All evaluations passed threshold$(NC)'); \
	" || exit 1
	@echo "$(GREEN)✓ CI evaluation passed$(NC)"

# Create LangSmith dataset
dataset-create: ensure-setup
	@if [ -z "$(DATASET)" ]; then \
		echo "$(RED)Error: DATASET variable required$(NC)"; \
		echo "Usage: make dataset-create DATASET=panos-agent-eval-v1"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating LangSmith dataset: $(DATASET)$(NC)"
	@$(PYTHON) scripts/evaluate.py --create-dataset --dataset $(DATASET) || exit 1
	@echo "$(GREEN)✓ Dataset created$(NC)"
	@echo ""
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)Dataset Template Guide$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@$(PYTHON) scripts/dataset_template.py
	@echo ""
	@echo "$(GREEN)Tip:$(NC) Use this template to create custom datasets"
	@echo "      Save as Python file, then: make dataset-create DATASET=your-dataset-name"

# Show dataset template
dataset-template: ensure-setup
	@echo "$(BLUE)Dataset Template Guide$(NC)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@$(PYTHON) scripts/dataset_template.py

# List LangSmith datasets
dataset-list: ensure-setup
	@echo "$(BLUE)Listing LangSmith datasets...$(NC)"
	@$(PYTHON) -c " \
		import os; \
		from langsmith import Client; \
		api_key = os.getenv('LANGSMITH_API_KEY'); \
		if not api_key: \
			print('$(YELLOW)Warning: LANGSMITH_API_KEY not set$(NC)'); \
			print('Set it in .env file or environment'); \
			exit(0); \
		client = Client(api_key=api_key); \
		datasets = list(client.list_datasets()); \
		if not datasets: \
			print('No datasets found'); \
		else: \
			print('Datasets:'); \
			for ds in datasets: \
				print(f'  - {ds.name} (ID: {ds.id})'); \
	" || echo "$(YELLOW)Note: Requires LANGSMITH_API_KEY$(NC)"

# Delete LangSmith dataset
dataset-delete: ensure-setup
	@if [ -z "$(DATASET)" ]; then \
		echo "$(RED)Error: DATASET variable required$(NC)"; \
		echo "Usage: make dataset-delete DATASET=panos-agent-eval-v1"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Warning: This will delete dataset: $(DATASET)$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PYTHON) -c " \
			import os; \
			from langsmith import Client; \
			api_key = os.getenv('LANGSMITH_API_KEY'); \
			if not api_key: \
				print('$(RED)Error: LANGSMITH_API_KEY not set$(NC)'); \
				exit(1); \
			client = Client(api_key=api_key); \
			dataset = client.read_dataset(dataset_name='$(DATASET)'); \
			client.delete_dataset(dataset_id=dataset.id); \
			print('$(GREEN)✓ Dataset deleted$(NC)'); \
		" || exit 1; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# Run tests
test: ensure-setup
	@echo "$(BLUE)Running tests...$(NC)"
	@$(PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

# Run linters
lint: ensure-setup
	@echo "$(BLUE)Running linters...$(NC)"
	@$(PYTHON) -m ruff check src/ tests/ scripts/ || true
	@$(PYTHON) -m flake8 src/ tests/ scripts/ || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

# Format code
format: ensure-setup
	@echo "$(BLUE)Formatting code...$(NC)"
	@$(PYTHON) -m black src/ tests/ scripts/
	@$(PYTHON) -m isort src/ tests/ scripts/
	@echo "$(GREEN)✓ Formatting complete$(NC)"

# Run all checks
check: lint format test
	@echo "$(GREEN)✓ All checks passed$(NC)"

# Clean up
clean:
	@echo "$(BLUE)Cleaning up...$(NC)"
	@rm -rf $(VENV)
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf __pycache__
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# CI-specific target (assumes venv doesn't persist)
ci-setup: check-uv
	@echo "$(BLUE)Setting up for CI...$(NC)"
	@$(UV) venv --python $(PYTHON_VERSION) $(VENV)
	@$(UV) pip install -e ".[dev]"
	@echo "$(GREEN)✓ CI setup complete$(NC)"

# CI evaluation (doesn't assume venv exists)
ci-evaluate: ci-setup
	@$(MAKE) evaluate-ci

