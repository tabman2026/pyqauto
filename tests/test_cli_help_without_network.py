from __future__ import annotations

import socket

import pytest

from pyqauto.cli import main

HELP_COMMANDS = [
    ["--help"],
    ["realtime", "--help"],
    ["full", "--help"],
    ["index", "--help"],
    ["minute", "--help"],
    ["daily", "--help"],
    ["kline", "--help"],
    ["kline", "000001", "--period", "15m", "--count", "10", "--help"],
    ["diagnose", "--help"],
    ["probe-pytdx", "--help"],
    ["source-schema-probe-live", "--help"],
]


@pytest.mark.parametrize("argv", HELP_COMMANDS)
def test_cli_help_commands_do_not_connect_network(
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("CLI help must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == 0
    assert "usage:" in capsys.readouterr().out
