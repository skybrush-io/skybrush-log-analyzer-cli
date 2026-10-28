import tomllib
from pathlib import Path

import platformdirs

from .errors import ConfigError

_CONFIG_FILENAME = "config.toml"
_TOKEN_FILENAME = "token.txt"  # noqa: S105


class ConfigPath:
    @classmethod
    def dir(cls, *, local: bool) -> Path:
        """Config directory in the given scope."""
        if local:
            return Path.cwd() / ".skybrush-log-analyzer"

        return platformdirs.user_config_path("skybrush-log-analyzer")


def has_config_file(config_dir: Path) -> bool:
    """Whether the given config directory has a config file."""
    return (config_dir / _CONFIG_FILENAME).is_file()


def read_config_file(config_dir: Path) -> dict[str, str]:
    """
    Reads the flat string settings of the config file in the given config directory.

    Returns an empty dict for a missing or unparseable file.
    """
    return _read_toml(config_dir / _CONFIG_FILENAME)


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


def delete_api_key(config_dir: Path) -> None:
    """
    Removes the API key from the config file of the given config directory and
    clears the corresponding token if it exists.

    A project-local config file is deleted. Any other config file is
    rewritten with its remaining flat string settings, losing comments and
    any other values, and deleted when no setting is left in it, which
    includes an unparseable file.

    Raises:
        ConfigError: The config file or the token could not be updated.
    """
    path = config_dir / _CONFIG_FILENAME
    try:
        data = {} if config_dir == ConfigPath.dir(local=True) else _read_toml(path)
        data.pop("api_key", None)
        if data:
            _write_toml(path, data)
        else:
            path.unlink(missing_ok=True)
    except OSError as e:
        raise ConfigError(str(e)) from e

    clear_token(config_dir)


def load_token(config_dir: Path) -> str | None:
    """Loads the token saved in the given config directory if it exists."""
    try:
        token = (config_dir / _TOKEN_FILENAME).read_text().strip()
    except OSError:
        return None
    return token or None


def save_token(config_dir: Path, token: str) -> None:
    """
    Saves the given token in the given config directory, creating it as needed.

    Raises:
        ConfigError: The token could not be saved.
    """
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / _TOKEN_FILENAME).write_text(token)
    except OSError as e:
        raise ConfigError(str(e)) from e


def clear_token(config_dir: Path) -> None:
    """
    Deletes the token saved in the given config directory if it exists.

    Raises:
        ConfigError: The token could not be deleted.
    """
    try:
        (config_dir / _TOKEN_FILENAME).unlink(missing_ok=True)
    except OSError as e:
        raise ConfigError(str(e)) from e


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
