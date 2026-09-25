import hashlib
import json
from typing import Any


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def print_json(data: Any) -> None:
    """Dumps the given data to JSON and prints the result."""
    print(json.dumps(data, ensure_ascii=False, allow_nan=False))
