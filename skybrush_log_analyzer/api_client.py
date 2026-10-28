from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import IO, Any, Self

import httpx2

from .auth_client import AuthClient
from .config import Config, delete_api_key, load_config, save_api_key
from .errors import (
    APIUnreachable,
    BadRequest,
    ConfigError,
    NotFound,
    ResponseParsingFailed,
    ServerError,
    Unauthenticated,
    UnknownTests,
)
from .typing import SuggestionCategory, TestGroup
from .utils import calculate_file_hash, set_query_params


class APIClient:
    __slots__ = ("_auth", "_config")

    def __init__(self, config: Config) -> None:
        self._config = config
        self._auth = AuthClient(config)

    @classmethod
    def login(cls, config_dir: Path, api_key: str, *, api_url: str | None = None) -> Self:
        """
        Validates the given API key and stores it in the config file of the given config directory.

        The account and API URLs are taken from that config file. A given `api_url`
        is used instead of the stored one, and stored along with the API key.

        On failure, the config file is left unchanged and the token stored in the
        config directory is cleared.

        Returns:
            A client using the validated API key.

        Raises:
            Unauthenticated: The API rejected the token acquired with the API key.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            APIUnreachable: The API could not be reached.
            ConfigError: The token or the API key could not be stored.
            ApplicationError: The API could not validate the token.
        """
        config = load_config(config_dir)
        client = cls(
            replace(config, api_key=api_key, api_url=config.api_url if api_url is None else api_url)
        )
        try:
            client.verify_credentials()
            save_api_key(config_dir, api_key, api_url=api_url)
        except BaseException:
            # The stored token may belong to the API key that failed to log in.
            with suppress(ConfigError):
                client.config.clear_token()
            raise
        return client

    @property
    def config(self) -> Config:
        return self._config

    def logout(self) -> None:
        """
        Invalidates the client, so any further request raises `Unauthenticated`,
        then removes the API key and the token from the config.

        Raises:
            ConfigError: The API key or the token could not be removed.
        """
        self._auth.invalidate()
        delete_api_key(self._config)

    def verify_credentials(self) -> None:
        """
        Acquires a fresh API token and checks that the API accepts it.

        Raises:
            Unauthenticated: No API key is configured, or the API rejected the token.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            APIUnreachable: The API could not be reached.
            ConfigError: The token could not be stored.
            ApplicationError: The API could not validate the token.
        """
        self._auth.refresh_token()
        self.version()

    def version(self) -> dict[str, Any]:
        return _json_object(self.request("/version"))

    def tests(self, group: str = "default") -> list[dict[str, Any]]:
        if group == "all":
            # No "all" listing route on the backend; merge the two listings.
            merged: list[dict[str, Any]] = []
            seen: set[str | None] = set()
            for listing in (self.request("/tests"), self.request("/tests/extras")):
                for test in _json_object_list(listing):
                    name = test.get("name")
                    if name not in seen:
                        seen.add(name)
                        merged.append(test)
            return merged
        return _json_object_list(self.request("/tests/extras" if group == "extra" else "/tests"))

    def validate_test_names(self, names: list[str], group: TestGroup = "default") -> None:
        """
        Checks that all the given test names belong to the given test group.

        Raises:
            UnknownTests: Some of the test names are not in the test group.
        """
        known = {test.get("name") for test in self.tests(group)}
        if unknown := [name for name in names if name not in known]:
            raise UnknownTests(f"Unknown test(s) in the {group} group: {', '.join(unknown)}")

    def analyze(self, path: Path, *, test_names: list[str] | None = None) -> dict[str, Any]:
        """
        Uploads the given log file, runs the analysis on it, and returns the stored analysis.

        Runs only the given tests when test names are given, after validating them
        against the full test listing.

        Raises:
            UnknownTests: Some of the test names are not in any test group.
        """
        if test_names is not None:
            self.validate_test_names(test_names, "all")
        # Refresh the API token before file upload to try to avoid hitting
        # token expiration during the operation.
        self._auth.refresh_token()
        # POST returns the new run only; test results live on the merged by-hash view.
        with path.open("rb") as f:
            self.request(
                "/analysis/",
                method="POST",
                files={"file": (path.name, f, "application/octet-stream")},
                data={"test_names": test_names} if test_names is not None else None,
                timeout=30,
            )

        return self.get_analysis(path)

    def get_web_login_url(self, *, intent: str | None = None) -> str:
        """Acquires a web login URL for the user, optionally with a web view intent."""
        login_url = _json_object(self.request("/login-ticket/", method="POST")).get("login_url")
        if not isinstance(login_url, str) or not login_url:
            raise ResponseParsingFailed()
        if intent is not None:
            login_url = set_query_params(login_url, intent=intent)
        return login_url

    def suggest(self, *, category: SuggestionCategory, title: str, content: str) -> dict[str, Any]:
        response = self.request(
            "/suggestion/",
            method="POST",
            json={
                "category": category,
                "title": title,
                "content": content,
            },
        )
        return _json_object(response)

    def get_suggestions(self, *, released: bool | None = None) -> list[dict[str, Any]]:
        response = self.request(
            "/suggestion/",
            params={"released": released} if released is not None else None,
        )
        return _json_object_list(response)

    def get_analysis(self, path: Path, *, extras: bool = False) -> dict[str, Any]:
        suffix = "/extras" if extras else ""
        response = self.request(
            f"/analysis/by-hash/{calculate_file_hash(path.read_bytes())}{suffix}",
            params={"filename": path.name},
        )
        return _json_object(response)

    def get_analysis_view_intent(self, path: Path) -> str:
        """Returns the web view intent for the analysis of the given log file."""
        result = self.request(
            f"/analysis/by-hash/{calculate_file_hash(path.read_bytes())}/intent",
            params={"filename": path.name},
        )
        intent = _json_object(result).get("intent")
        if not isinstance(intent, str) or not intent:
            raise ResponseParsingFailed()
        return intent

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, IO[bytes], str]] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: int | float = 5,
    ) -> Any:
        response = self._send_request(
            path,
            method=method,
            data=data,
            files=files,
            params=params,
            json=json,
            timeout=timeout,
        )

        if response.status_code == 401:
            self._auth.refresh_token()
            # File bodies may have been consumed; rewind when possible.
            if files is not None:
                for _, file_obj, _ in files.values():
                    seek = getattr(file_obj, "seek", None)
                    if callable(seek):
                        seek(0)
            response = self._send_request(
                path,
                method=method,
                data=data,
                files=files,
                params=params,
                json=json,
                timeout=timeout,
            )
            if response.status_code == 401:
                raise Unauthenticated()

        status_code = response.status_code
        if 400 <= status_code < 500:
            error = NotFound if status_code == 404 else BadRequest
            raise error(f"HTTP {status_code}: {response.text}")

        if status_code >= 500:
            raise ServerError()

        try:
            return response.json()
        except Exception as e:
            raise ResponseParsingFailed() from e

    def _send_request(
        self,
        path: str,
        *,
        method: str,
        data: dict[str, Any] | None,
        files: dict[str, tuple[str, IO[bytes], str]] | None,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int | float,
    ) -> httpx2.Response:
        try:
            with httpx2.Client(
                base_url=self._config.api_url,
                headers=self._auth.make_auth_headers(),
                timeout=timeout,
            ) as client:
                return client.request(method, path, files=files, data=data, params=params, json=json)
        except httpx2.HTTPError as e:
            raise APIUnreachable(str(e)) from e


def _json_object(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ResponseParsingFailed()
    return data


def _json_object_list(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ResponseParsingFailed()
    return data
