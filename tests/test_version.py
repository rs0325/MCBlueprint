import pytest

import mcblueprint
from mcblueprint.cli import EXIT_USAGE_ERROR, main


def test_version_is_defined() -> None:
    assert mcblueprint.__version__


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert mcblueprint.__version__ in capsys.readouterr().out


def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == EXIT_USAGE_ERROR
    assert "usage:" in capsys.readouterr().out
