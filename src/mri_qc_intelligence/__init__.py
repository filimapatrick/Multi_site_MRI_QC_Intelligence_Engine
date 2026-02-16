"""MRI QC Intelligence Engine.

Automated Multi-Site MRI Quality Control Intelligence Engine.
"""

__version__ = "0.1.0"
__author__ = "Patrick Filima"
__email__ = "patrick.filima@example.com"

from .core import QCEngine
from .data_loader import BIDSLoader
from .scoring import QCScorer
from .reporting import ReportGenerator

__all__ = [
    "QCEngine",
    "BIDSLoader", 
    "QCScorer",
    "ReportGenerator",
]