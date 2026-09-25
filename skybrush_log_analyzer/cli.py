import shutil
from pathlib import Path
from typing import Annotated

import typer

from .analysis import to_agent_view
from .api_client import APIClient
from .auth_client import AuthClient
from .config import Config, describe_config_location, load_config, login, logout
from .errors import (
    AccountUnreachable,
    ApplicationError,
    BadRequest,
    ConfigError,
    InvalidAPIKey,
    ResponseParsingFailed,
    ServerError,
    Unauthenticated,
    typer_error_handler,
)
from .paths import ConfigPath, DestinationPath, ResourcePath
from .typing import SuggestionCategory, TestGroup
from .utils import print_json

app = typer.Typer(
    name="ArduPilot log analysis CLI",
    help="CLI application for ArduPilot log analysis services provided by the Skybrush.io team.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

config = load_config()
auth = AuthClient(config)
client = APIClient(config, auth)


@app.command()
def version() -> None:
    """Show analysis backend version info."""
    with typer_error_handler(config):
        print_json(client.version())


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
    with typer_error_handler(config):
        print_json(client.tests(group))


@app.command()
def analyze(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    test: Annotated[
        list[str] | None,
        typer.Option(
            "--test",
            "-t",
            help="Test name to run (repeatable). Omit to run all tests.",
        ),
    ] = None,
) -> None:
    """Upload the given log file, run the analysis on it, and print the results."""
    if not file.is_file():
        print(f"Log file not found: {file}")
        raise typer.Exit(code=1)

    with typer_error_handler(config):
        # Refresh the API token before file upload to try to avoid hitting
        # token expiration during the operation.
        auth.refresh_token()
        result = client.analyze(file, test_names=test)
        print_json(to_agent_view(result))


@app.command(name="get-analysis")
def get_analysis(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Print the raw API response without trimming."),
    ] = False,
) -> None:
    """Fetch existing analysis for the given log file."""
    if not file.is_file():
        print(f"Log file not found: {file}")
        raise typer.Exit(code=1)

    with typer_error_handler(config):
        result = client.get_analysis(file)
        print_json(result if raw else to_agent_view(result))


@app.command(name="get-analysis-extras")
def get_analysis_extras(
    file: Annotated[Path, typer.Argument(help="Path to the ArduPilot log file.")],
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Print the raw API response without trimming."),
    ] = False,
) -> None:
    """Fetch the extra, verbose test results for the given log file."""
    if not file.is_file():
        print(f"Log file not found: {file}")
        raise typer.Exit(code=1)

    with typer_error_handler(config):
        result = client.get_analysis(file, extras=True)
        print_json(result if raw else to_agent_view(result))


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

    with typer_error_handler(config):
        result = client.suggest(category=category, title=title, content=content)
        print_json(result)


@app.command(name="login")
def login_cmd(
    api_key: Annotated[str, typer.Option(prompt="API key")],
    local: Annotated[
        bool,
        typer.Option("--local", help="Whether to update the local config instead of the global one."),
    ] = False,
) -> None:
    """Log in with a Skybrush API key."""
    candidate = Config(
        api_key=api_key,
        api_url=config.api_url,
        account_url=config.account_url,
        config_dir=ConfigPath.dir(local=local),
    )
    candidate_auth = AuthClient(candidate)
    candidate_client = APIClient(candidate, candidate_auth)

    with typer_error_handler(candidate):
        # Mint a fresh token with the candidate key and check backend acceptance.
        candidate_auth.refresh_token()
        candidate_client.version()
        try:
            login(api_key, local=local)
        except OSError as e:
            raise ConfigError(str(e)) from e
    print("Logged in.")


@app.command(name="logout")
def logout_cmd() -> None:
    """Log out."""
    if config.api_key is None:
        print("Not logged in.")
        raise typer.Exit(code=1)

    with typer_error_handler(config):
        try:
            logout(config)
        except OSError as e:
            raise ConfigError(str(e)) from e
    print(f"Logged out ({describe_config_location(config)}).")


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
    source = ResourcePath.skill()
    dest = DestinationPath.skill(local=local, claude=claude)
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

    print(f"Using {describe_config_location(config)}.")
    try:
        auth.refresh_token()
        client.version()
        print(f"Authenticated at {config.account_url}.")
    except InvalidAPIKey:
        print(f"API key is invalid or has been revoked. Create a new one at {config.account_url}.")
        raise typer.Exit(code=1) from None
    except AccountUnreachable:
        print(f"Could not reach {config.account_url} to refresh the API token.")
        raise typer.Exit(code=1) from None
    except Unauthenticated:
        print("Backend rejected the API token.")
        raise typer.Exit(code=1) from None
    except (BadRequest, ResponseParsingFailed, ServerError):
        print("Backend could not validate the API token.")
        raise typer.Exit(code=1) from None
    except ApplicationError:
        print("Authentication status check failed.")
        raise typer.Exit(code=1) from None
