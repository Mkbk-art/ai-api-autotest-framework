"""Deterministic API Contract coverage analysis.

The package name deliberately avoids ``coverage`` so it cannot shadow the
third-party coverage.py package used by pytest-cov.
"""

from coverage_engine.gap import CoverageGap
from coverage_engine.index import CoverageIndex

__all__ = ["CoverageGap", "CoverageIndex"]
