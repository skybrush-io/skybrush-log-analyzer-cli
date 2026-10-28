from dataclasses import dataclass
from pathlib import Path
from typing import Self

from ._config_store import ConfigPath, has_config_file, read_config_file

_DEFAULT_API_URL = "https://logs.skybrush.io/api/v1"
_DEFAULT_ACCOUNT_URL = "https://account.skybrush.io"


@dataclass(kw_only=True, frozen=True, slots=True)
class Config:
    """Application config."""

    account_url: str
    """URL of the Skybrush account that issues API tokens for the API key."""

    api_key: str | None
    """The API key, or `None` when the config has none."""

    api_url: str
    """URL of the Skybrush Log Analyzer API."""

    config_dir: Path
    """The directory the config was loaded from."""

    @classmethod
    def load(cls, config_dir: Path | None = None) -> Self:
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
            config_dir = local_dir if has_config_file(local_dir) else ConfigPath.dir(local=False)

        data = read_config_file(config_dir)
        return cls(
            api_key=data.get("api_key"),
            api_url=data.get("api_url", _DEFAULT_API_URL),
            account_url=data.get("account_url", _DEFAULT_ACCOUNT_URL),
            config_dir=config_dir,
        )
