"""Smoke test for the pyplecs CLI and webgui integration."""

import subprocess
import sys
import unittest


class SmokeTests(unittest.TestCase):
    def test_cli_starts(self):
        """Ensure the CLI entrypoint script runs without immediate crash."""
    # Importing the startup script should not raise.
    # We explicitly avoid launching the uvicorn server.
        cmd = (
            "import importlib, start_webgui; "
            "print('START_WEBGUI_IMPORTED')"
        )
        try:
            result = subprocess.run(
                [sys.executable, '-c', cmd],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.fail('Importing start_webgui timed out')

        output = (result.stdout or '') + (result.stderr or '')
        self.assertIn('START_WEBGUI_IMPORTED', output)


if __name__ == '__main__':
    unittest.main()
