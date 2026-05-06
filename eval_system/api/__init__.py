"""Top-level API layer for the evaluation system."""

from .facade import EvaluationAPI

EvaluationRunner = EvaluationAPI

__all__ = ["EvaluationAPI", "EvaluationRunner"]
