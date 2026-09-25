from __future__ import annotations

from typing import TYPE_CHECKING

import httpx2

from .errors import AccountUnreachable, InvalidAPIKey, Unauthenticated

if TYPE_CHECKING:
    from .config import Config


class AuthClient:
    """Acquires and stores API tokens from the account."""

    __slots__ = ("_config", "_token")

    def __init__(self, config: Config) -> None:
        self._config = config
        self._token: str | None = None

    def make_auth_headers(self) -> dict[str, str]:
        """
        Returns authorization headers for API requests.

        Raises:
            Unauthenticated: No API key is configured.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
        """
        return {"Authorization": f"Bearer {self._get_token()}"}

    def refresh_token(self) -> None:
        """
        Discards any stored token and acquires a new one.

        Raises:
            Unauthenticated: No API key is configured.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
        """
        # Invalidate everything
        self._token = None
        self._config.clear_token()
        # Request fresh token
        self._request_new_token()

    def _get_token(self) -> str:
        """
        Returns token from memory, storage, or a fresh token request.

        Raises:
            Unauthenticated: No API key is configured.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
        """
        if self._token is not None:
            return self._token

        token = self._config.load_token()
        if token is not None:
            self._token = token
            return token

        return self._request_new_token()

    def _request_new_token(self) -> str:
        """
        Acquires a new token and stores it.

        Raises:
            Unauthenticated: No API key is configured.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
        """
        if not self._config.api_key:
            raise Unauthenticated()

        try:
            with httpx2.Client(base_url=self._config.account_url, timeout=5) as client:
                response = client.post(
                    "/api/get-api-token",
                    json={"apiKey": self._config.api_key},
                )
        except httpx2.HTTPError as e:
            raise AccountUnreachable(str(e)) from e

        if response.status_code in (401, 403):
            raise InvalidAPIKey("API key rejected by account app")

        if response.status_code != 200:
            raise AccountUnreachable(f"Unexpected status from account app: {response.status_code}")

        try:
            body = response.json()
        except Exception as e:
            raise AccountUnreachable("Account app returned non-JSON response") from e

        token = body.get("result") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise AccountUnreachable("Account app response missing token result")

        self._config.save_token(token)
        self._token = token
        return token
