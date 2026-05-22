# tests/test_main.py
import subprocess
import sys


def test_main_help():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "prepare" in result.stdout
    assert "start" in result.stdout
    assert "report" in result.stdout


def test_main_prepare_command():
    result = subprocess.run(
        [sys.executable, "main.py", "prepare", "--company", "TestCorp", "--role", "Dev", "--type", "tech"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "TestCorp" in result.stdout
