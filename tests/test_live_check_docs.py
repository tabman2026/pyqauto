from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_NAMES = [
    "LIVE_CHECK.md",
    "TROUBLESHOOTING.md",
    "KLINE_GUIDE.md",
    "DATA_SOURCES.md",
    "CLI_REFERENCE.md",
]


def _combined_docs() -> str:
    parts = [(ROOT / "README.md").read_text(encoding="utf-8")]
    parts.extend((ROOT / "docs" / name).read_text(encoding="utf-8") for name in DOC_NAMES)
    return "\n".join(parts)


def test_docs_explain_kline_pytdx_only_and_no_easyquotation_fallback() -> None:
    text = _combined_docs()

    assert "K-line APIs are pytdx-only" in text
    assert "K-line APIs never use easyquotation fallback" in text
    assert "K-line failures do not use easyquotation fallback" in text


def test_docs_explain_pytdx_probe_and_active_local_pool() -> None:
    text = _combined_docs()

    assert (
        "aquote-router probe-pytdx --json --output "
        "config/pytdx_servers.active.local.json"
    ) in text
    assert "--pytdx-servers config/pytdx_servers.active.local.json --json" in text
    assert "config/pytdx_servers.active.local.json" in text
    assert "should not be committed" in text
    assert "Free pytdx server availability changes" in text
    assert "not a guarantee" in text


def test_docs_do_not_add_blocked_workflows() -> None:
    text = _combined_docs()
    blocked_terms = [
        "Q" + "MT",
        "券" + "商",
        "真实" + "交易",
        "候选" + "股池",
        "买卖" + "点",
        "收益" + "率",
        "胜" + "率",
    ]

    for term in blocked_terms:
        assert term not in text
