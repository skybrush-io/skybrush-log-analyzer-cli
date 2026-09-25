from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import ConfigPath

_DEFAULT_API_URL = "https://logs.skybrush.io/api/v1"
_DEFAULT_ACCOUNT_URL = "https://account.skybrush.io"
_CONFIG_FILENAME = "config.toml"
_TOKEN_FILENAME = "token.txt"


@dataclass(kw_only=True, frozen=True, slots=True)
class Config:
    """Application config."""

    account_url: str
    api_key: str | None
    api_url: str
    config_dir: Path

    @property
    def token_path(self) -> Path:
        return self.config_dir / _TOKEN_FILENAME

    def load_token(self) -> str | None:
        """Loads the saved token if it exists."""
        try:
            token = self.token_path.read_text().strip()
        except OSError:
            return None
        return token or None

    def save_token(self, token: str) -> None:
        """Saves the given token, creating parent directories as needed."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(token)

    def clear_token(self) -> None:
        """Deletes the saved token if it exists."""
        try:
            self.token_path.unlink()
        except FileNotFoundError:
            pass


def load_config() -> Config:
    """
    Loads the application config.

    Config directory search order:

    - Project-local: `<current-working-directory>/.skybrush-log-analyzer/`
    - Global: `<user-config-dir>/skybrush-log-analyzer/`
    """
    for directory in (ConfigPath.dir(local=True), ConfigPath.dir(local=False)):
        path = directory / _CONFIG_FILENAME
        if path.is_file():
            data = _read_toml(path)
            return Config(
                api_key=data.get("api_key"),
                api_url=data.get("api_url", _DEFAULT_API_URL),
                account_url=data.get("account_url", _DEFAULT_ACCOUNT_URL),
                config_dir=directory,
            )

    return Config(
        api_key=None,
        api_url=_DEFAULT_API_URL,
        account_url=_DEFAULT_ACCOUNT_URL,
        config_dir=ConfigPath.dir(local=False),
    )


def login(api_key: str, *, local: bool = False) -> None:
    """
    Stores the given API key in the application's config file.

    Arguments:
        api_key: The API key to store.
        local: Whether the project-local or the global config file
            should be updated.
    """
    path = ConfigPath.dir(local=local) / _CONFIG_FILENAME
    data = _read_toml(path)
    data["api_key"] = api_key
    _write_toml(path, data)


def logout(config: Config) -> None:
    """
    Removes the config file for the given `Config` and
    clears the corresponding token if it exists.

    """
    try:
        (config.config_dir / _CONFIG_FILENAME).unlink()
    except FileNotFoundError:
        pass

    config.clear_token()


def describe_config_location(config: Config) -> str:
    """Human-readable label for the config directory corresponding to the given config."""
    if config.config_dir == ConfigPath.dir(local=True):
        return f"local config at {config.config_dir}"
    if config.config_dir == ConfigPath.dir(local=False):
        return f"global config at {config.config_dir}"
    return f"custom config at {config.config_dir}"


def _read_toml(path: Path) -> dict[str, str]:
    """
    Reads the given toml file, returning only flat string values.

    Returns an empty dict for a missing or unparseable file.
    """
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        import warnings

        warnings.warn(f"Ignoring unparseable config file {path}: {e}", stacklevel=2)
        return {}

    # Keep flat string values only; ignore anything else.
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _write_toml(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'{k} = "{_escape(v)}"' for k, v in data.items()]
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def _escape(value: str) -> str:
    # Minimal TOML basic-string escaping.
    return value.replace("\\", "\\\\").replace('"', '\\"')
