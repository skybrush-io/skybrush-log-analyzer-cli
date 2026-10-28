from typing import Any


def select_tests(analysis: dict[str, Any], test_names: list[str]) -> dict[str, Any]:
    """Returns the analysis with only the results of the given tests kept."""
    selected = set(test_names)
    return {
        **analysis,
        "test_results": [
            result for result in analysis.get("test_results") or [] if result.get("test_name") in selected
        ],
    }


def drop_pass_messages(analysis: dict[str, Any]) -> dict[str, Any]:
    """Returns the analysis with the messages of passing test results omitted."""
    return {
        **analysis,
        "test_results": [
            {key: value for key, value in result.items() if key != "messages"}
            if result.get("status") == "PASS"
            else result
            for result in analysis.get("test_results") or []
        ],
    }


def compact(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Returns the compact view of an analysis API response.

    Keeps the backend core version (always present, even when null), the note,
    the status counts, and the test results with their name, status, title and
    messages. Test results and status counts are ordered by severity. Drops
    internal IDs and null fields.
    """
    tests = [
        _test_view(result)
        for result in sorted(
            analysis.get("test_results") or [],
            key=lambda result: _STATUS_RANK.get(result.get("status"), len(_STATUS_RANK)),
        )
    ]
    view = {
        "note_title": analysis.get("note_title"),
        "note_description": analysis.get("note_description"),
        "status_counts": _status_counts(tests),
        "test_results": tests,
    }
    return {"paplan_version": analysis.get("paplan_version"), **_without_none_fields(view)}


_STATUS_RANK = {
    status: rank
    for rank, status in enumerate(
        (
            "FAIL",
            "WARN",
            "INFO",
            "PASS",
            "SKIP",
            "NOT_APPLICABLE",
        )
    )
}

_MESSAGE_FIELDS = ("text", "value", "unit", "severity", "timestamp")


def _test_view(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages") or []
    view: dict[str, Any] = {
        "test_name": result.get("test_name"),
        "status": result.get("status"),
        "title": result.get("title"),
    }
    if messages:
        view["messages"] = [_message_view(message) for message in messages]
    return _without_none_fields(view)


def _message_view(message: dict[str, Any]) -> dict[str, Any]:
    return {key: message[key] for key in _MESSAGE_FIELDS if message.get(key) is not None}


def _status_counts(tests: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for test in tests:
        status = test.get("status")
        if status is not None:
            counts[status] = counts.get(status, 0) + 1
    return counts


def _without_none_fields(view: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in view.items() if value is not None}
