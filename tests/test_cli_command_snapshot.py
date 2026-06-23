from __future__ import annotations

import pytest

from pyqauto.cli import CLI_COMMANDS, build_parser, main

EXPECTED_COMMANDS = {
    "daily",
    "diagnose",
    "full",
    "index",
    "kline",
    "minute",
    "probe-pytdx",
    "realtime",
    "source-schema-probe-live",
}


def _parser_commands() -> set[str]:
    parser = build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and choices:
            return set(choices)
    return set()


def test_cli_command_snapshot_is_frozen() -> None:
    assert CLI_COMMANDS == EXPECTED_COMMANDS
    assert _parser_commands() == EXPECTED_COMMANDS


def test_kline_help_is_available(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["kline", "--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "--period" in captured.out
    assert "--count" in captured.out


def test_kline_help_accepts_frozen_invocation_shape(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["kline", "000001", "--period", "15m", "--count", "10", "--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "usage: pyqauto kline" in captured.out
