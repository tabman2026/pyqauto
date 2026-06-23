from __future__ import annotations

import builtins
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from astock_source_router.adapters.pytdx_adapter import PytdxAdapter
from astock_source_router.core.errors import SourceUnavailableError
from pyqauto.cli import build_parser


def test_pytdx_dependency_contract_is_core_dependency() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    dependencies_block = text.split("dependencies = [", 1)[1].split("]", 1)[0]

    assert '"pytdx>=1.72"' in dependencies_block


def test_base_imports_do_not_require_pytdx() -> None:
    import pyqauto
    from pyqauto import QuoteRouter

    assert pyqauto.__version__
    assert QuoteRouter is not None


def test_cli_parser_build_does_not_require_pytdx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def blocked_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "pytdx" or name.startswith("pytdx."):
            raise ModuleNotFoundError("blocked pytdx import")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    parser = build_parser()

    assert parser.prog == "pyqauto"


def test_pytdx_adapter_reports_clear_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def blocked_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "pytdx" or name.startswith("pytdx."):
            raise ModuleNotFoundError("blocked pytdx import")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    adapter = PytdxAdapter(server_pool=[("127.0.0.1", 7709)])

    with pytest.raises(SourceUnavailableError) as exc_info:
        adapter._tdx()

    message = str(exc_info.value)
    assert "pytdx is required" in message
    assert "pyqauto" in message
