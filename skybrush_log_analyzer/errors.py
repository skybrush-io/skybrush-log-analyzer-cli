from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from .config import Config


class ApplicationError(Exception):
    """Base class for errors raised by the CLI application."""


class ApplicationErrorWithMessage(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

    @property
    def message(self) -> str:
        return str(self.args[0])


class ConfigError(ApplicationErrorWithMessage): ...


class Unauthenticated(ApplicationError): ...


class InvalidAPIKey(ApplicationErrorWithMessage): ...


class AccountUnreachable(ApplicationErrorWithMessage): ...


class BadRequest(ApplicationErrorWithMessage): ...


class ServerError(ApplicationError): ...


class ResponseParsingFailed(ApplicationError): ...


@contextmanager
def typer_error_handler(config: Config) -> Iterator[None]:  # noqa: C901
    try:
        yield
    except Unauthenticated as e:
        print("Authentication error. Check your API key.")
        raise typer.Exit(1) from e
    except InvalidAPIKey as e:
        print(f"Your API key is invalid or has been revoked. Create a new one at {config.account_url}.")
        raise typer.Exit(1) from e
    except AccountUnreachable as e:
        print(f"Could not reach {config.account_url} to acquire an API token.")
        raise typer.Exit(1) from e
    except BadRequest as e:
        print(f"Bad request: {e.message}")
        raise typer.Exit(1) from e
    except ConfigError as e:
        print(f"Config error: {e.message}")
        raise typer.Exit(1) from e
    except ServerError as e:
        print("An error occurred on the server.")
        raise typer.Exit(1) from e
    except ResponseParsingFailed as e:
        print("Server returned non-JSON response.")
        raise typer.Exit(1) from e
    except ApplicationErrorWithMessage as e:
        print(f"An unexpected error occurred: {e.message}")
        raise typer.Exit(1) from e
    except ApplicationError as e:
        print("An unexpected error occurred.")
        raise typer.Exit(1) from e
    except Exception as e:
        print("An unexpected error occurred.")
        raise typer.Exit(1) from e
