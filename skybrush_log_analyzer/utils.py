import hashlib
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def set_query_params(url: str, **params: str) -> str:
    """
    Sets the given query params on the URL.

    If a set param was present in `url`, it is overwritten with the new value.
    """
    parts = urlsplit(url)
    query = [
        *(
            (name, value)
            for name, value in parse_qsl(parts.query, keep_blank_values=True)
            if name not in params
        ),
        *params.items(),
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def print_json(data: Any) -> None:
    """Dumps the given data to JSON and prints the result."""
    print(json.dumps(data, ensure_ascii=False, allow_nan=False))
