#!/usr/bin/env python3
"""Setup script for MRI QC Intelligence Engine."""

from setuptools import setup, find_packages

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mri-qc-intelligence",
    version="0.1.0",
    author="Patrick Filima",
    author_email="patrick.filima@example.com",
    description="Automated Multi-Site MRI Quality Control Intelligence Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/patrick-filima/mri-qc-intelligence",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
            "pre-commit>=2.15.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "qc_engine=mri_qc_intelligence.cli:main",
            "qc_api=mri_qc_intelligence.api:main",
        ],
    },
    keywords="mri neuroimaging quality-control bids multi-site",
    project_urls={
        "Bug Reports": "https://github.com/patrick-filima/mri-qc-intelligence/issues",
        "Documentation": "https://mri-qc-intelligence.readthedocs.io/",
        "Source": "https://github.com/patrick-filima/mri-qc-intelligence",
    },
)