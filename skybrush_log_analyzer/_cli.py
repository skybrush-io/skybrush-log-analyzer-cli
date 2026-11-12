import importlib.resources
import json
import shutil
import webbrowser
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from ._config_store import ConfigPath
from .analysis import compact, drop_pass_messages, select_tests
from .api_client import APIClient
from .config import Config
from .errors import (
    AccountUnreachable,
    APIUnreachable,
    ApplicationError,
    ApplicationErrorWithMessage,
    BadRequest,
    ConfigError,
    InvalidAPIKey,
    NotFound,
    ResponseParsingFailed,
    ServerError,
    Unauthenticated,
    UnknownTests,
)
from .typing import SuggestionCategory, TestGroup

app = typer.Typer(
    name="ArduPilot log analysis CLI",
    help="CLI application for ArduPilot log analysis services provided by the Skybrush.io team.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

config = Config.load()
client = APIClient(config)

DetailedOption = Annotated[
    bool,
    typer.Option("--detailed", help="Include the messages of passing tests too."),
]
TestOption = Annotated[
    list[str] | None,
    typer.Option(
        "--test",
        "-t",
        help="Test name to include in the output (repeatable). Omit to include all tests.",
    ),
]


@app.command()
def web(
    file: Annotated[
        Path | None,
        typer.Argument(help="Optional log file analysis to open.", show_default=False),
    ] = None,
) -> None:
    """
    Open the Skybrush Log Analyzer web application. Optionally provide a file path
    to open the analysis of that file.
    """
    with _typer_error_handler():
        if file is not None and not file.is_file():
            print(f"Log file not found: {file}")
            raise typer.Exit(code=1)

        intent = None
        if file is not None:
            try:
                intent = client.get_analysis_view_intent(file)
            except NotFound:
                print(f"No analysis found for {file}, opening the web application without it.")
        url = client.get_web_login_url(intent=intent)
        print(f"Opening {url} ...")
        webbrowser.open(url)


@app.command()
def account() -> None:
    """Open the Skybrush account page in the default browser."""
    print(f"Opening {config.account_url} ...")
    webbrowser.open(config.account_url)


@app.command()
def version() -> None:
    """Show analysis backend version info."""
    with _typer_error_handler():
        _print_json(client.version())


@app.command()
def tests(
    group: Annotated[
        TestGroup,
        typer.Argument(
            help="Test group to list: the default tests, the extra (verbose) ones, or all of them."
        ),
    ] = "default",
) -> None:
    """List available ArduPilot log tests."""
    with _typer_error_handler():
        _print_json(client.tests(group))


@app.command()
def analyze(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    detailed: DetailedOption = False,
    test: TestOption = None,
) -> None:
    """Upload the given log file, run the analysis on it, and print the results."""
    _check_log_file(file)
    with _typer_error_handler():
        result = client.analyze(file, test_names=test)
        _print_analysis(result, detailed=detailed, tests=test)


@app.command(name="get-analysis")
def get_analysis(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    detailed: DetailedOption = False,
    test: TestOption = None,
) -> None:
    """Fetch existing analysis for the given log file."""
    _check_log_file(file)
    with _typer_error_handler():
        if test:
            client.validate_test_names(test, "default")
        result = _get_stored_analysis(file, extras=False)
        _print_analysis(result, detailed=detailed, tests=test)


@app.command(name="get-analysis-extras")
def get_analysis_extras(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    detailed: DetailedOption = False,
    test: TestOption = None,
) -> None:
    """Fetch the extra, verbose test results for the given log file."""
    _check_log_file(file)
    with _typer_error_handler():
        if test:
            client.validate_test_names(test, "extra")
        result = _get_stored_analysis(file, extras=True)
        _print_analysis(result, detailed=detailed, tests=test)


@app.command(name="suggest")
def suggest(
    content: Annotated[
        str,
        typer.Argument(
            help="Feedback content (10-2000 characters). "
            "Describe the error noticed, the missing log test, or the user feedback."
        ),
    ],
    title: Annotated[
        str,
        typer.Option(
            "--title", "-t", help="Short summary (1-100 characters, excluding surrounding whitespace)."
        ),
    ],
    category: Annotated[
        SuggestionCategory,
        typer.Option(
            "--category", "-c", help="Feedback category. Use 'test_case' for missing or improved log tests."
        ),
    ],
) -> None:
    """Submit feedback about the analysis service to the Skybrush team."""
    content = content.strip()
    if not (10 <= len(content) <= 2000):
        raise typer.BadParameter(
            "Feedback content must be 10-2000 characters long (excluding surrounding whitespace)."
        )

    title = title.strip()
    if not (1 <= len(title) <= 100):
        raise typer.BadParameter(
            "Feedback title must be 1-100 characters long (excluding surrounding whitespace)."
        )

    with _typer_error_handler():
        result = client.suggest(category=category, title=title, content=content)
        _print_json(result)


@app.command()
def suggestions(
    unreleased: Annotated[
        bool,
        typer.Option(
            "--unreleased",
            help="List only feedback that has not been released yet. Omit to list all feedback.",
        ),
    ] = False,
) -> None:
    """List previously submitted feedback."""
    with _typer_error_handler():
        _print_json(client.get_suggestions(released=False if unreleased else None))


@app.command(name="login")
def login_cmd(
    api_key: Annotated[str, typer.Option(prompt="API key")],
    api_url: Annotated[
        str | None,
        typer.Option("--api-url", help="Analysis API URL to use and store, e.g. a local backend."),
    ] = None,
    local: Annotated[
        bool,
        typer.Option("--local", help="Whether to update the local config instead of the global one."),
    ] = False,
) -> None:
    """Log in with a Skybrush API key."""
    with _typer_error_handler():
        APIClient.login(ConfigPath.dir(local=local), api_key, api_url=api_url)
    print("Logged in.")


@app.command(name="logout")
def logout_cmd() -> None:
    """Log out."""
    if config.api_key is None:
        print("Not logged in.")
        raise typer.Exit(code=1)

    with _typer_error_handler():
        client.logout()
    print(f"Logged out ({_describe_config_location(config)}).")


@app.command(name="add-skill")
def add_skill(
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing skill installation."),
    ] = False,
    local: Annotated[
        bool,
        typer.Option(
            "--local", help="Whether to install into the project-local or the global skills directory."
        ),
    ] = False,
    claude: Annotated[
        bool,
        typer.Option("--claude", help="Whether to install for Claude Code."),
    ] = False,
) -> None:
    """Install the bundled agent skill for the current user."""
    source = _ResourcePath.skill()
    dest = _DestinationPath.skill(local=local, claude=claude)
    if dest.exists():
        if not force:
            print(f"{dest} already exists, use --force to overwrite.")
            raise typer.Exit(code=1)
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    print(f"Skill installed in {dest}.")


@app.command()
def auth_status() -> None:
    """Show current Skybrush account authentication status."""
    if config.api_key is None:
        print("No API key configured. Use the login command to log in.")
        raise typer.Exit(code=1)

    print(f"Using {_describe_config_location(config)}.")
    try:
        client.verify_credentials()
        print(f"Authenticated at {config.account_url}.")
    except InvalidAPIKey:
        print(f"API key is invalid or has been revoked. Create a new one at {config.account_url}.")
        raise typer.Exit(code=1) from None
    except AccountUnreachable:
        print(f"Could not reach {config.account_url} to refresh the API token.")
        raise typer.Exit(code=1) from None
    except APIUnreachable:
        print(f"Could not reach {config.api_url} to validate the API token.")
        raise typer.Exit(code=1) from None
    except Unauthenticated:
        print("Backend rejected the API token.")
        raise typer.Exit(code=1) from None
    except BadRequest as e:
        print(f"Backend could not validate the API token: {e.message}")
        raise typer.Exit(code=1) from None
    except (ResponseParsingFailed, ServerError):
        print("Backend could not validate the API token.")
        raise typer.Exit(code=1) from None
    except ApplicationError:
        print("Authentication status check failed.")
        raise typer.Exit(code=1) from None


def run() -> None:
    app()


def _check_log_file(file: Path) -> None:
    """Validates the log file and raises exception on error."""
    if not file.is_file():
        print(f"Log file not found: {file}")
        raise typer.Exit(code=1)


def _get_stored_analysis(file: Path, *, extras: bool) -> dict[str, Any]:
    """Fetches the stored analysis of the given log file, exiting with a hint when there is none."""
    try:
        return client.get_analysis(file, extras=extras)
    except NotFound:
        print(f"No analysis found for {file}. Run the analyze command to create it.")
        raise typer.Exit(code=1) from None


def _print_analysis(analysis: dict[str, Any], *, detailed: bool, tests: list[str] | None) -> None:
    """
    Prints the compact view of an analysis API response.

    With test names given, keeps only the results of the given tests. Omits the
    messages of passing tests unless detailed output is requested.
    """
    if tests:
        analysis = select_tests(analysis, tests)
    if not detailed:
        analysis = drop_pass_messages(analysis)
    view = compact(analysis)
    if not view["test_results"]:
        view["note"] = "No test results in this group; run the analyze command to produce them."
    _print_json(view)


@contextmanager
def _typer_error_handler() -> Iterator[None]:  # noqa: C901
    try:
        yield
    except typer.Exit:
        raise
    except Unauthenticated as e:
        print("Authentication error. Check your API key.")
        raise typer.Exit(1) from e
    except InvalidAPIKey as e:
        print(f"Your API key is invalid or has been revoked. Create a new one at {e.url}.")
        raise typer.Exit(1) from e
    except AccountUnreachable as e:
        print(f"Could not reach {e.url} to acquire an API token.")
        raise typer.Exit(1) from e
    except APIUnreachable as e:
        print(f"Could not reach {e.url}.")
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
        print("Server returned an unexpected response.")
        raise typer.Exit(1) from e
    except UnknownTests as e:
        print(f"{e.message}. Use the tests command to list the available tests.")
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


def _describe_config_location(config: Config) -> str:
    """Human-readable label for the config directory corresponding to the given config."""
    if config.config_dir == ConfigPath.dir(local=True):
        return f"local config at {config.config_dir}"
    if config.config_dir == ConfigPath.dir(local=False):
        return f"global config at {config.config_dir}"
    return f"custom config at {config.config_dir}"


def _print_json(data: Any) -> None:
    """Dumps the given data to JSON and prints the result."""
    print(json.dumps(data, ensure_ascii=False, allow_nan=False))


class _ResourcePath:
    @classmethod
    def skill(cls) -> Path:
        """Path to the bundled agent skill."""
        return cls._resources_root() / "skills" / "skybrush-log-analysis"

    @classmethod
    def _resources_root(cls) -> Path:
        """Path to the root of the bundled resources."""
        return cast(Path, importlib.resources.files("skybrush_log_analyzer") / "resources")


class _DestinationPath:
    @classmethod
    def skill(cls, *, local: bool, claude: bool = False) -> Path:
        """Installation path of the agent skill in the given scope."""
        base = Path.cwd() if local else Path.home()
        harness_dir = ".claude" if claude else ".agents"
        return base / harness_dir / "skills" / "skybrush-log-analysis"


if __name__ == "__main__":
    run()
