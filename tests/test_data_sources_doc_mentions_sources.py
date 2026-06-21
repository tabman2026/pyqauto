from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_data_sources_doc_mentions_sources_and_kline_rule() -> None:
    text = (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8")

    for source in ["pytdx", "akshare_em_spot", "easyquotation_sina", "easyquotation_tencent"]:
        assert source in text
    assert "K-line APIs never use easyquotation fallback" in text
    assert "does not produce market data" in text
