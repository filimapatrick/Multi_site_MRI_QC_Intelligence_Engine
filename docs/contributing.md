# Contributing to MRI QC Intelligence Engine

🎉 Thank you for your interest in contributing! This project aims to advance automated QC in neuroimaging, and we welcome contributions from the community.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)



## Getting Started

### Prerequisites

- Python 3.8+
- Git
- Familiarity with neuroimaging data formats (NIfTI, BIDS)
- Basic understanding of MRI physics and quality control concepts

### Areas for Contribution

1. **Core Algorithms**: Implement new QC metrics or improve existing ones
2. **Multi-site Harmonization**: Enhance cross-site standardization methods
3. **Visualization**: Create better plots and interactive dashboards
4. **Documentation**: Improve user guides, tutorials, and API docs
5. **Testing**: Add test cases and improve code coverage
6. **Performance**: Optimize computation speed and memory usage
7. **Integration**: Add support for new data formats or platforms

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/filimapatrick/mri-qc-intelligence.git
cd mri-qc-intelligence
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Installation

```bash
# Run tests to ensure everything works
pytest tests/

# Check code style
black --check src/ tests/
flake8 src/ tests/
mypy src/
```

## How to Contribute

### Reporting Bugs

1. **Check existing issues** first to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Provide minimal reproducible examples** when possible
4. **Include system information**: OS, Python version, package versions

### Suggesting Enhancements

1. **Check existing feature requests** to avoid duplicates
2. **Use the feature request template**
3. **Provide scientific justification** for new metrics or methods
4. **Include references** to relevant literature when applicable

### Contributing Code

1. **Create a new branch** for your feature/bugfix:
   ```bash
   git checkout -b feature/new-metric-name
   ```

2. **Make focused commits** with clear messages:
   ```bash
   git commit -m "Add temporal SNR calculation for fMRI QC"
   ```

3. **Add tests** for new functionality

4. **Update documentation** as needed

5. **Submit a pull request** following our template

## Coding Standards

### Python Style

- Follow **PEP 8** guidelines
- Use **Black** for automatic code formatting
- Use **type hints** for all function signatures
- Maximum line length: **88 characters** (Black default)

### Code Organization

```python
# Example function structure
def compute_metric(data: np.ndarray, 
                  mask: Optional[np.ndarray] = None,
                  **kwargs) -> Dict[str, float]:
    """Compute quality control metric.
    
    Parameters
    ----------
    data : np.ndarray
        Input image data
    mask : np.ndarray, optional
        Brain mask for computation
    **kwargs
        Additional parameters
        
    Returns
    -------
    dict
        Computed metrics
        
    Raises
    ------
    ValueError
        If data dimensions are invalid
    """
    # Input validation
    if data.ndim < 3:
        raise ValueError("Expected 3D or 4D data")
        
    # Main computation
    result = _internal_computation(data, mask)
    
    # Return standardized format
    return {'metric_name': result}
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `QCMetrics`)
- **Functions/Variables**: `snake_case` (e.g., `compute_snr`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_THRESHOLD`)
- **Private methods**: `_leading_underscore` (e.g., `_validate_input`)

### Documentation Strings

Use **NumPy-style docstrings**:

```python
def example_function(param1: int, param2: str) -> bool:
    """One-line summary of function.
    
    Longer description if needed. Include scientific background
    and references where appropriate.
    
    Parameters
    ----------
    param1 : int
        Description of first parameter
    param2 : str
        Description of second parameter
        
    Returns
    -------
    bool
        Description of return value
        
    Examples
    --------
    >>> example_function(42, "test")
    True
    
    References
    ----------
    .. [1] Smith et al., "Paper Title", Journal, Year.
    """
    pass
```

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory
- Mirror the `src/` structure in `tests/`
- Use descriptive test names: `test_snr_computation_with_zero_noise`

### Test Categories

1. **Unit Tests**: Test individual functions/methods
2. **Integration Tests**: Test component interactions
3. **Regression Tests**: Ensure bug fixes remain fixed
4. **Performance Tests**: Monitor computation speed

### Writing Tests

```python
import pytest
import numpy as np
from mri_qc_intelligence.metrics import T1QCMetrics

class TestT1QCMetrics:
    """Test suite for T1w QC metrics."""
    
    def test_snr_computation_normal_case(self):
        """Test SNR computation with typical values."""
        metrics = T1QCMetrics()
        signal = np.array([100, 110, 90])
        noise = np.array([5, 3, 7])
        
        snr = metrics.compute_snr(signal, noise)
        
        assert snr > 0
        assert isinstance(snr, float)
        
    def test_snr_computation_zero_noise(self):
        """Test SNR computation with zero noise."""
        metrics = T1QCMetrics()
        signal = np.array([100, 100, 100])
        noise = np.array([0, 0, 0])
        
        snr = metrics.compute_snr(signal, noise)
        
        assert snr == np.inf
        
    @pytest.mark.parametrize("signal,noise,expected", [
        ([100, 100, 100], [10, 10, 10], 10.0),
        ([50, 50, 50], [5, 5, 5], 10.0),
    ])
    def test_snr_parametrized(self, signal, noise, expected):
        """Test SNR with multiple parameter sets."""
        metrics = T1QCMetrics()
        result = metrics.compute_snr(np.array(signal), np.array(noise))
        assert abs(result - expected) < 1e-10
```

### Mock Data and Fixtures

Use fixtures for reusable test data:

```python
@pytest.fixture
def sample_t1_data():
    """Generate realistic T1w test data."""
    # Create 3D brain-like data
    data = np.random.rand(64, 64, 32) * 100
    # Add brain-like structure
    data[16:48, 16:48, 8:24] += 50
    return data
```

## Documentation

### API Documentation

- All public functions/classes must have docstrings
- Use **Sphinx** for generating API docs
- Include examples in docstrings where helpful

### User Documentation

- Update `README.md` for major feature additions
- Add tutorials to `docs/tutorials/`
- Include scientific background in `docs/scientific_background.md`

### Building Documentation

```bash
# Generate API documentation
cd docs/
sphinx-apidoc -o . ../src/mri_qc_intelligence
make html

# View documentation
open _build/html/index.html
```

## Pull Request Process

### Before Submitting

1. **Run all tests**:
   ```bash
   pytest tests/ --cov=mri_qc_intelligence
   ```

2. **Check code quality**:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

3. **Update documentation** if needed

4. **Ensure CI passes** on your fork

### Pull Request Template

Use our template to provide:

- **Clear description** of changes
- **Motivation** for the changes
- **Testing performed**
- **Breaking changes** (if any)
- **Related issues**

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Scientific review** for new metrics/methods
4. **Documentation review** for user-facing changes

## Release Process

### Version Numbering

We follow **Semantic Versioning** (semver.org):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. Update version in `setup.py` and `__init__.py`
2. Update `CHANGELOG.md`
3. Create release branch: `release/v1.2.3`
4. Final testing and documentation review
5. Merge to main and tag release
6. Publish to PyPI
7. Create GitHub release with artifacts

## Scientific Contributions

### New QC Metrics

When adding new metrics:

1. **Provide scientific justification** and literature references
2. **Validate against existing methods** where possible
3. **Include parameter tuning guidelines**
4. **Document clinical significance** and interpretation

### Algorithm Improvements

For enhancing existing algorithms:

1. **Benchmark against current implementation**
2. **Provide performance comparisons**
3. **Ensure backward compatibility** when possible
4. **Document parameter changes**

## Getting Help

### Communication Channels

- **GitHub Discussions**: General questions and announcements
- **Issues**: Bug reports and feature requests
- **Email**: Maintainer contact for sensitive issues

### Maintainers

- **Patrick Filima** ([@patrick-filima](https://github.com/patrick-filima)) - Project Lead

We appreciate your contributions and look forward to building better neuroimaging QC tools together! 🧠✨