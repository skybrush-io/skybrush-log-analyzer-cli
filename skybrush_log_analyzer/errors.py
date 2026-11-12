class ApplicationError(Exception):
    """Base class for the errors of this package."""


class ApplicationErrorWithMessage(ApplicationError):
    """Base class for the errors of this package that carry a message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @property
    def message(self) -> str:
        """The message of the error."""
        return str(self.args[0])


class ApplicationErrorWithURL(ApplicationErrorWithMessage):
    """Base class for the errors of this package that concern the service at a URL."""

    def __init__(self, message: str, *, url: str) -> None:
        super().__init__(message)
        self._url = url

    @property
    def url(self) -> str:
        """The URL of the service the error concerns."""
        return self._url


class ConfigError(ApplicationErrorWithMessage):
    """The config could not be read or written."""


class Unauthenticated(ApplicationError):
    """No API key is configured, the client was logged out, or the API rejected the token."""


class InvalidAPIKey(ApplicationErrorWithURL):
    """The account rejected the API key."""


class AccountUnreachable(ApplicationErrorWithURL):
    """The account could not be reached or returned an unexpected response."""


class APIUnreachable(ApplicationErrorWithURL):
    """The API could not be reached."""


class BadRequest(ApplicationErrorWithMessage):
    """The API rejected the request with a client error status."""


class NotFound(BadRequest):
    """The requested resource does not exist."""


class ServerError(ApplicationError):
    """The API failed with a server error status."""


class ResponseParsingFailed(ApplicationError):
    """The API returned a response of unexpected format."""


class UnknownTests(ApplicationErrorWithMessage):
    """Some of the given test names are not in the given test group."""
