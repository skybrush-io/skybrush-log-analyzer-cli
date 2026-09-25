import importlib.resources
from pathlib import Path
from typing import cast

import platformdirs


class ResourcePath:
    @classmethod
    def skill(cls) -> Path:
        """Path to the bundled agent skill."""
        return cls._resources_root() / "skills" / "skybrush-log-analysis"

    @classmethod
    def _resources_root(cls) -> Path:
        """Path to the root of the bundled resources."""
        return cast(Path, importlib.resources.files("skybrush_log_analyzer") / "resources")


class DestinationPath:
    @classmethod
    def skill(cls, *, local: bool, claude: bool = False) -> Path:
        """Installation path of the agent skill in the given scope."""
        base = Path.cwd() if local else Path.home()
        harness_dir = ".claude" if claude else ".agents"
        return base / harness_dir / "skills" / "skybrush-log-analysis"


class ConfigPath:
    @classmethod
    def dir(cls, *, local: bool) -> Path:
        """Config directory in the given scope."""
        if local:
            return Path.cwd() / ".skybrush-log-analyzer"

        return platformdirs.user_config_path("skybrush-log-analyzer")
