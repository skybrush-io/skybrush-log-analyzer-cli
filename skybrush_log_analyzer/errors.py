class ApplicationError(Exception):
    """Base class for the errors of this package."""


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


class APIUnreachable(ApplicationErrorWithMessage): ...


class BadRequest(ApplicationErrorWithMessage): ...


class NotFound(BadRequest): ...


class ServerError(ApplicationError): ...


class ResponseParsingFailed(ApplicationError): ...


class UnknownTests(ApplicationErrorWithMessage): ...
