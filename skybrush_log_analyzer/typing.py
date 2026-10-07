from typing import Literal

TestGroup = Literal["default", "extra", "all"]

SuggestionCategory = Literal["test_case", "feature", "improvement", "bug", "other"]

SuggestionStatus = Literal["pending", "reviewed", "implemented", "rejected"]
