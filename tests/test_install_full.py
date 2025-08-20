import sys
import subprocess
import pytest

from pyplecs.cli import installer


def test_full_install_flow(monkeypatch):
    # Mock install_packages to avoid real pip installs
    def fake_install(packages, auto_yes=False):
        return {'installed': packages, 'failed': [], 'skipped': [], 'missing': []}

    monkeypatch.setattr(installer, 'install_packages', fake_install)

    # Mock system install to avoid running brew/apt
    def fake_sys_install(pkgs, auto_yes=False):
        return {'installed': pkgs, 'failed': [], 'attempted': pkgs}

    monkeypatch.setattr(installer, 'install_system_packages', fake_sys_install)

    # Call CLI main with --full
    rc = installer.main(['install-packages', '--full', '--yes'])
    assert rc == 0
