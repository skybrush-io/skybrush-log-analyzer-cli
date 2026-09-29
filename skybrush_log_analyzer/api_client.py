from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import httpx2

from .errors import BadRequest, ResponseParsingFailed, ServerError, Unauthenticated
from .typing import SuggestionCategory
from .utils import calculate_file_hash

if TYPE_CHECKING:
    from .auth_client import AuthClient
    from .config import Config


@dataclass(frozen=True, slots=True)
class APIClient:
    config: Config
    auth: AuthClient

    def version(self) -> Any:
        return self.request("/version")

    def tests(self, group: str = "default") -> Any:
        if group == "all":
            # No "all" listing route on the backend; merge the two listings.
            merged: list[dict[str, Any]] = []
            seen: set[str] = set()
            for listing in (self.request("/tests"), self.request("/tests/extras")):
                for test in listing:
                    name = test.get("name")
                    if name not in seen:
                        seen.add(name)
                        merged.append(test)
            return merged
        return self.request("/tests/extras" if group == "extra" else "/tests")

    def analyze(self, path: Path, *, test_names: list[str] | None = None) -> Any:
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

    def get_web_login_url(self) -> str:
        """Acquires a web login URL for the user."""
        link = self.request("/login-ticket/", method="POST")
        login_url = link.get("login_url") if isinstance(link, dict) else None
        if not isinstance(login_url, str) or not login_url:
            raise ResponseParsingFailed()
        return login_url

    def suggest(self, *, category: SuggestionCategory, title: str, content: str) -> Any:
        return self.request(
            "/suggestion/",
            method="POST",
            json={
                "category": category,
                "title": title,
                "content": content,
            },
        )

    def get_analysis(self, path: Path, *, extras: bool = False) -> Any:
        suffix = "/extras" if extras else ""
        return self.request(
            f"/analysis/by-hash/{calculate_file_hash(path.read_bytes())}{suffix}",
            params={"filename": path.name},
        )

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
            self.auth.refresh_token()
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
            print(f"Request failed ({status_code}): {response.text}")
            raise BadRequest(response.text)

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
        with httpx2.Client(
            base_url=self.config.api_url,
            headers=self.auth.make_auth_headers(),
            timeout=timeout,
        ) as client:
            return client.request(method, path, files=files, data=data, params=params, json=json)
