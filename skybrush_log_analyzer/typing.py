from typing import Literal

TestGroup = Literal["default", "extra", "all"]
"""Test group: the default tests, the extra (verbose) ones, or all of them."""

SuggestionCategory = Literal["test_case", "feature", "improvement", "bug", "other"]
"""Category of feedback submitted about the analysis service."""
