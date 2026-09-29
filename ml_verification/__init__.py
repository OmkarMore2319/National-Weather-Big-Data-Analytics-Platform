"""
ML Verification Package for National Weather Big Data Analytics Platform (PS 26069).
Provides standalone event classification, duplicate detection, and trust scoring.
"""

from .engine import classify_and_score, preload_models

__all__ = ["classify_and_score", "preload_models"]
