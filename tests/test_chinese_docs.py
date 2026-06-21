from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_doc(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_chinese_readme_and_docs_entry_exist() -> None:
    assert (ROOT / "README.zh-CN.md").exists()
    assert (ROOT / "docs" / "zh-CN" / "README.md").exists()
    assert (ROOT / "docs" / "GITHUB_ABOUT_SETUP.md").exists()


def test_readme_links_chinese_readme() -> None:
    readme = read_doc("README.md")

    assert "README.zh-CN.md" in readme


def test_chinese_readme_covers_required_topics() -> None:
    text = read_doc("README.zh-CN.md")

    for expected in [
        "A股行情",
        "15分钟K线",
        "日K",
        "probe-pytdx",
        "不提供投资建议",
        "source",
        "source_level",
        "trace_id",
        "pytdx",
        "easyquotation",
        "Sina",
        "Tencent",
        "数据源 fallback",
        "JSONL",
        "SQLite",
    ]:
        assert expected in text


def test_chinese_docs_do_not_introduce_forbidden_trading_features() -> None:
    texts = "\n".join(
        [
            read_doc("README.md"),
            read_doc("README.zh-CN.md"),
            read_doc("docs/zh-CN/README.md"),
            read_doc("docs/GITHUB_ABOUT_SETUP.md"),
        ]
    )
    forbidden_terms = [
        "Q" + "MT",
        "券" + "商",
        "真实" + "交易",
        "候选" + "股池",
        "买卖" + "点",
        "收益" + "率",
        "胜" + "率",
    ]

    for term in forbidden_terms:
        assert term not in texts


def test_chinese_docs_do_not_leak_local_paths() -> None:
    texts = "\n".join(
        [
            read_doc("README.md"),
            read_doc("README.zh-CN.md"),
            read_doc("docs/zh-CN/README.md"),
            read_doc("docs/GITHUB_ABOUT_SETUP.md"),
        ]
    )

    assert "C:\\Users" not in texts
    assert "Desktop/CODEX" not in texts
