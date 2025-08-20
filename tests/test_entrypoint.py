import subprocess
import sys


def test_entrypoint_help():
    # Call the installed console script and check it returns 0 and prints help
    cmd = [sys.executable.replace('python', 'pyplecs-setup') if 'python' in sys.executable else 'pyplecs-setup', '--help']
    # Fallback to direct module call
    try:
        res = subprocess.run(['pyplecs-setup', '--help'], capture_output=True, text=True)
        assert res.returncode == 0
        assert 'PyPLECS setup helper' in res.stdout
    except FileNotFoundError:
        # fallback: call as module
        res = subprocess.run([sys.executable, '-m', 'pyplecs.cli.installer', '--help'], capture_output=True, text=True)
        assert res.returncode == 0
        assert 'PyPLECS setup helper' in res.stdout
