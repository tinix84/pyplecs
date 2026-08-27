import subprocess
import sys
from pathlib import Path

import pyplecs

REPO_ROOT = Path(__file__).parent.parent


def test_band1_contracts_are_publicly_exported():
    expected = {
        "ParameterVector",
        "ParametricStudy",
        "ParametricStudyStatus",
        "TasCapture",
        "TasCompilation",
        "TasCompilationError",
        "TasCompiler",
        "TasDiagnostic",
        "TasExecutionEnvelope",
        "TasExecutionService",
    }

    assert expected <= set(pyplecs.__all__)
    assert all(getattr(pyplecs, name) is not None for name in expected)


def test_tas_import_remains_available_without_web_dependencies():
    code = """
import builtins

original_import = builtins.__import__
def without_fastapi(name, *args, **kwargs):
    if name == "fastapi" or name.startswith("fastapi."):
        raise ImportError("blocked optional web dependency")
    return original_import(name, *args, **kwargs)

builtins.__import__ = without_fastapi
import pyplecs
from pyplecs import ParametricStudy, TasExecutionService
assert ParametricStudy is not None
assert TasExecutionService is not None
assert pyplecs.create_api_app is None
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
