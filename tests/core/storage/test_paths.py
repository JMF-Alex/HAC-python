import os
import sys

from core.storage import paths
from core.constants import APP_NAME


def test_user_data_dir_honours_the_override(tmp_path, monkeypatch):
    target = tmp_path / "custom" / "dir"
    monkeypatch.setenv("HAC_CONFIG_DIR", str(target))

    assert paths.user_data_dir() == str(target)
    assert target.is_dir()


def test_user_data_dir_defaults_to_an_app_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("HAC_CONFIG_DIR", raising=False)
    for variable in ("APPDATA", "XDG_CONFIG_HOME", "HOME", "USERPROFILE"):
        monkeypatch.setenv(variable, str(tmp_path))

    result = paths.user_data_dir()

    assert os.path.basename(result) == APP_NAME
    assert result.startswith(str(tmp_path))
    assert os.path.isdir(result)


def test_resource_path_uses_the_pyinstaller_bundle(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", "bundle", raising=False)
    assert paths.resource_path("assets", "icon.ico") == os.path.join("bundle", "assets", "icon.ico")


def test_resource_path_falls_back_to_the_source_root(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    source_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(paths.__file__))))
    assert paths.resource_path("assets", "icon.ico") == os.path.join(source_root, "assets", "icon.ico")


def test_the_bundled_icon_is_found_from_source(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert os.path.isfile(paths.resource_path("assets", "icon.ico"))
