.PHONY: help install install-dev test test-coverage lint format type-check clean docs docs-serve build docker-build docker-run release

# Default target
help: ## Show this help message
	@echo "MRI QC Intelligence Engine - Make Commands"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install package in development mode
	pip install -e .

install-dev: ## Install package with development dependencies
	pip install -e ".[dev]"
	pre-commit install

##@ Testing

test: ## Run tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=mri_qc_intelligence --cov-report=html --cov-report=term

test-fast: ## Run tests excluding slow integration tests
	pytest tests/ -v -m "not slow"

##@ Code Quality

lint: ## Run linting (flake8)
	flake8 src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting without making changes
	black --check src/ tests/

type-check: ## Run type checking with mypy
	mypy src/

quality-check: format-check lint type-check ## Run all code quality checks

##@ Documentation

docs: ## Build documentation
	cd docs && make html

docs-serve: docs ## Build and serve documentation locally
	cd docs/_build/html && python -m http.server 8080

docs-clean: ## Clean documentation build
	cd docs && make clean

##@ Build and Release

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	python setup.py sdist bdist_wheel

docker-build: ## Build Docker image
	docker build -t mri-qc-intelligence:latest .

docker-run: ## Run Docker container with sample data
	docker run --rm -it \
		-v ${PWD}/sample_data:/data \
		-v ${PWD}/output:/output \
		mri-qc-intelligence:latest \
		--bids-dir /data --output-dir /output

##@ Sample Data and Testing

sample-analysis: ## Run analysis on sample data
	qc_engine --bids-dir sample_data --output-dir sample_output --format html json

create-sample-config: ## Create sample configuration file
	cp qc_config.yaml sample_config.yaml
	@echo "Sample configuration created: sample_config.yaml"

##@ CI/CD

ci-test: install-dev quality-check test-coverage ## Run full CI test suite

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

##@ Release Management

check-version: ## Check current version
	@python -c "import mri_qc_intelligence; print(f'Current version: {mri_qc_intelligence.__version__}')"

release-check: clean quality-check test build docs ## Run pre-release checks

release-test: release-check ## Test release on PyPI test server
	twine upload --repository testpypi dist/*

release: release-check ## Upload release to PyPI
	twine upload dist/*

tag-release: ## Create and push git tag for release
	@echo "Current version: $$(python -c 'import mri_qc_intelligence; print(mri_qc_intelligence.__version__)')"
	@read -p "Create tag for this version? [y/N] " confirm && [ "$$confirm" = "y" ]
	git tag "v$$(python -c 'import mri_qc_intelligence; print(mri_qc_intelligence.__version__)')"
	git push origin "v$$(python -c 'import mri_qc_intelligence; print(mri_qc_intelligence.__version__)')"

##@ Environment Management

setup-dev: ## Set up complete development environment
	python -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install-dev"

update-deps: ## Update all dependencies
	pip-compile requirements.in --upgrade
	pip-compile requirements-dev.in --upgrade

##@ Utilities

count-lines: ## Count lines of code
	@find src/ -name "*.py" | xargs wc -l | tail -1
	@echo "Test lines:"
	@find tests/ -name "*.py" | xargs wc -l | tail -1

profile: ## Run performance profiling
	python -m cProfile -o profile.stats -m mri_qc_intelligence.cli --help
	python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

benchmark: ## Run benchmarking tests
	pytest tests/ -v -m "benchmark" --benchmark-only

##@ Information

info: ## Show project information
	@echo "MRI QC Intelligence Engine"
	@echo "=========================="
	@echo "Version: $$(python -c 'import mri_qc_intelligence; print(mri_qc_intelligence.__version__)' 2>/dev/null || echo 'Not installed')"
	@echo "Python: $$(python --version)"
	@echo "pip: $$(pip --version)"
	@echo "Git branch: $$(git branch --show-current 2>/dev/null || echo 'Not a git repo')"
	@echo "Git commit: $$(git rev-parse --short HEAD 2>/dev/null || echo 'Not a git repo')"
	@echo ""
	@echo "Dependencies status:"
	@python -c "import sys; print('✅ Python OK')" 2>/dev/null || echo "❌ Python issue"
	@python -c "import numpy; print('✅ NumPy:', numpy.__version__)" 2>/dev/null || echo "❌ NumPy not available"
	@python -c "import nibabel; print('✅ NiBabel:', nibabel.__version__)" 2>/dev/null || echo "❌ NiBabel not available"
	@python -c "import sklearn; print('✅ scikit-learn:', sklearn.__version__)" 2>/dev/null || echo "❌ scikit-learn not available"