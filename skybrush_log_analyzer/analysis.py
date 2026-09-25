from typing import Any


def to_agent_view(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Returns the compact, agent-facing view of an analysis API response.

    Drops internal IDs and null fields, orders test results by severity,
    counts the statuses, omits the messages of passing tests, and adds a
    note when there are no test results.
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
    if not tests:
        view["note"] = "No test results in this group; run the analyze command to produce them."
    return _without_none_fields(view)


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


def _test_view(result: dict[str, Any]) -> dict[str, Any]:
    messages = [] if result.get("status") == "PASS" else result.get("messages") or []
    view: dict[str, Any] = {
        "test_name": result.get("test_name"),
        "status": result.get("status"),
        "title": result.get("title"),
    }
    if messages:
        view["messages"] = [_message_view(message) for message in messages]
    return _without_none_fields(view)


def _message_view(message: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in message.items() if key != "id" and value is not None}


def _status_counts(tests: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for test in tests:
        status = test["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def _without_none_fields(view: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in view.items() if value is not None}
