import json
import tomllib
from pathlib import Path

from app.version import __version__


def test_public_version_metadata_stays_synchronized() -> None:
    repository = Path(__file__).parents[2]
    frontend = json.loads((repository / "frontend/package.json").read_text())
    backend = tomllib.loads((repository / "backend/pyproject.toml").read_text())

    assert __version__ == "0.1.0-dev.0"
    assert frontend["version"] == __version__
    assert backend["project"]["version"] == "0.1.0.dev0"
