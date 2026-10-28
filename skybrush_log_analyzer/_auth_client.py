from __future__ import annotations

from typing import TYPE_CHECKING

import httpx2

from ._config_store import clear_token, load_token, save_token
from .errors import AccountUnreachable, InvalidAPIKey, Unauthenticated

if TYPE_CHECKING:
    from .config import Config


class AuthClient:
    """Acquires and stores API tokens from the account."""

    __slots__ = ("_config", "_invalidated", "_token")

    def __init__(self, config: Config) -> None:
        self._config = config
        self._invalidated = False
        self._token: str | None = None

    def make_auth_headers(self) -> dict[str, str]:
        """
        Returns authorization headers for API requests.

        Raises:
            Unauthenticated: No API key is configured, or the client was invalidated.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            ConfigError: The token could not be stored.
        """
        return {"Authorization": f"Bearer {self._get_token()}"}

    def refresh_token(self) -> None:
        """
        Discards any stored token and acquires a new one.

        Raises:
            Unauthenticated: No API key is configured, or the client was invalidated.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            ConfigError: The token could not be cleared or stored.
        """
        if self._invalidated:
            raise Unauthenticated()
        self._token = None
        clear_token(self._config.config_dir)
        self._request_new_token()

    def invalidate(self) -> None:
        """Discards the token held in memory; any further token use raises `Unauthenticated`."""
        self._invalidated = True
        self._token = None

    def _get_token(self) -> str:
        """
        Returns token from memory, storage, or a fresh token request.

        Raises:
            Unauthenticated: No API key is configured, or the client was invalidated.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            ConfigError: The token could not be stored.
        """
        if self._invalidated or not self._config.api_key:
            raise Unauthenticated()
        if self._token is not None:
            return self._token

        token = load_token(self._config.config_dir)
        if token is not None:
            self._token = token
            return token

        return self._request_new_token()

    def _request_new_token(self) -> str:
        """
        Acquires a new token and stores it.

        Raises:
            Unauthenticated: No API key is configured, or the client was invalidated.
            InvalidAPIKey: The account rejected the API key.
            AccountUnreachable: The account could not be reached or returned an unexpected response.
            ConfigError: The token could not be stored.
        """
        if not self._config.api_key:
            raise Unauthenticated()

        account_url = self._config.account_url
        try:
            with httpx2.Client(base_url=account_url, timeout=5) as client:
                response = client.post(
                    "/api/get-api-token",
                    json={"apiKey": self._config.api_key},
                )
        except httpx2.HTTPError as e:
            raise AccountUnreachable(str(e), url=account_url) from e

        if response.status_code in (401, 403):
            raise InvalidAPIKey("API key rejected by account app", url=account_url)

        if response.status_code != 200:
            raise AccountUnreachable(
                f"Unexpected status from account app: {response.status_code}", url=account_url
            )

        try:
            body = response.json()
        except Exception as e:
            raise AccountUnreachable("Account app returned non-JSON response", url=account_url) from e

        token = body.get("result") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise AccountUnreachable("Account app response missing token result", url=account_url)

        # The client may have been invalidated while the token was being acquired.
        if self._invalidated:
            raise Unauthenticated()
        save_token(self._config.config_dir, token)
        self._token = token
        return token
