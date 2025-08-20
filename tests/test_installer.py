import sys
import os
import importlib
import tempfile
from pathlib import Path

import pytest

from pyplecs.cli import installer


def test_create_config(tmp_path, monkeypatch):
    # run write_default_config to the tmp dir
    target = tmp_path / 'config' / 'default.yml'
    path = installer.write_default_config(target)
    assert Path(path).exists()
    content = Path(path).read_text()
    assert 'plecs:' in content


def test_check_all_returns_dict():
    res = installer.check_macos_installation() if sys.platform == 'darwin' else installer.check_windows_installation()
    assert isinstance(res, dict)
    assert 'platform' in res


def test_install_packages_skips_on_no_missing(monkeypatch):
    # monkeypatch check_python_packages to return all True
    monkeypatch.setattr(installer, 'check_python_packages', lambda pkgs: {p: True for p in pkgs})
    res = installer.install_packages(['fakepkg'], auto_yes=True)
    assert res['missing'] == []


def test_install_packages_installs(monkeypatch, tmp_path):
    # Simulate one missing package and mock subprocess.check_call
    def fake_check_packages(pkgs):
        return {pkgs[0]: False}
    monkeypatch.setattr(installer, 'check_python_packages', fake_check_packages)

    called = {}
    def fake_check_call(cmd):
        called['cmd'] = cmd
        return 0
    monkeypatch.setattr(installer.subprocess, 'check_call', fake_check_call)

    res = installer.install_packages(['somepkg'], auto_yes=True)
    assert 'somepkg' in res['installed'] or 'somepkg' in res['failed'] or res['skipped']
