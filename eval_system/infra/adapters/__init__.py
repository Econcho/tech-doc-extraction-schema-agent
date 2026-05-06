"""Adapter modules exposed through the top-level infrastructure layer."""

from .base import DocumentAdapter
from .json_adapter import JsonAdapter
from .langextract_adapter import LangExtractAdapter

__all__ = ["DocumentAdapter", "JsonAdapter", "LangExtractAdapter"]
