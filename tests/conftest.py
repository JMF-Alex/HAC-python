import sys
from unittest.mock import MagicMock

import pytest

for _name in ("keyboard", "pynput", "pynput.keyboard", "pynput.mouse"):
    sys.modules[_name] = MagicMock()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HAC_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr("core.storage.config.LEGACY_CONFIG_PATH", str(tmp_path / "hac_config.json"))