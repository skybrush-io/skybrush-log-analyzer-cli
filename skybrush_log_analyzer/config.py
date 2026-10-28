from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError
from .paths import ConfigPath

_DEFAULT_API_URL = "https://logs.skybrush.io/api/v1"
_DEFAULT_ACCOUNT_URL = "https://account.skybrush.io"
_CONFIG_FILENAME = "config.toml"
_TOKEN_FILENAME = "token.txt"  # noqa: S105


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
        """
        Saves the given token, creating parent directories as needed.

        Raises:
            ConfigError: The token could not be saved.
        """
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(token)
        except OSError as e:
            raise ConfigError(str(e)) from e

    def clear_token(self) -> None:
        """
        Deletes the saved token if it exists.

        Raises:
            ConfigError: The token could not be deleted.
        """
        try:
            self.token_path.unlink(missing_ok=True)
        except OSError as e:
            raise ConfigError(str(e)) from e


def load_config(config_dir: Path | None = None) -> Config:
    """
    Loads the application config from the given config directory, using the
    defaults when it has no config file.

    Without a config directory, the first one with a config file is used,
    in this order:

    - Project-local: `<current-working-directory>/.skybrush-log-analyzer/`
    - Global: `<user-config-dir>/skybrush-log-analyzer/`

    The global one is used when neither has a config file.
    """
    if config_dir is None:
        local_dir = ConfigPath.dir(local=True)
        config_dir = local_dir if (local_dir / _CONFIG_FILENAME).is_file() else ConfigPath.dir(local=False)

    data = _read_toml(config_dir / _CONFIG_FILENAME)
    return Config(
        api_key=data.get("api_key"),
        api_url=data.get("api_url", _DEFAULT_API_URL),
        account_url=data.get("account_url", _DEFAULT_ACCOUNT_URL),
        config_dir=config_dir,
    )


def save_api_key(config_dir: Path, api_key: str, *, api_url: str | None = None) -> None:
    """
    Stores the given API key in the config file of the given config directory.

    The config file is rewritten with its flat string settings, losing
    comments and any other values.

    Arguments:
        config_dir: The config directory whose config file is updated.
        api_key: The API key to store.
        api_url: The API URL to store along with the API key, or `None`
            to leave it unchanged.

    Raises:
        ConfigError: The config file could not be read or written.
    """
    path = config_dir / _CONFIG_FILENAME
    try:
        data = _read_toml(path)
        data["api_key"] = api_key
        if api_url is not None:
            data["api_url"] = api_url
        _write_toml(path, data)
    except OSError as e:
        raise ConfigError(str(e)) from e


def delete_api_key(config: Config) -> None:
    """
    Removes the API key from the config file of the given `Config` and
    clears the corresponding token if it exists.

    A project-local config file is deleted. Any other config file is
    rewritten with its remaining flat string settings, losing comments and
    any other values, and deleted when no setting is left in it, which
    includes an unparseable file.

    Raises:
        ConfigError: The config file or the token could not be updated.
    """
    path = config.config_dir / _CONFIG_FILENAME
    try:
        data = {} if config.config_dir == ConfigPath.dir(local=True) else _read_toml(path)
        data.pop("api_key", None)
        if data:
            _write_toml(path, data)
        else:
            path.unlink(missing_ok=True)
    except OSError as e:
        raise ConfigError(str(e)) from e

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
