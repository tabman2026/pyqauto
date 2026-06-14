"""Release leak scanner for aquote-router."""

from __future__ import annotations

import sys
from pathlib import Path

BANNED_TERMS = [
    "QMT",
    "XtQuantTrader",
    "xtdata",
    "券商",
    "真实交易",
    "买入",
    "卖出",
    "仓位",
    "候选股池",
    "顶级游资盈利系统",
    "webhook",
    "token",
    "cookie",
    "secret",
    "C:\\Users\\weibiaowei",
    "/Users/",
    "Desktop/CODEX",
    "人工签署",
    "收益率",
    "胜率",
]

SCAN_SUFFIXES = {
    ".bat",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "logs",
}

SAFE_CONTEXT_MARKERS = [
    "不",
    "未",
    "禁止",
    "不要",
    "Do not",
    "does not",
    "without",
    "id-token",
    "Trusted Publishing",
    "是否包含",
    "forbidden",
]


def collect_violations(root: Path) -> list[tuple[Path, int, str, str]]:
    violations: list[tuple[Path, int, str, str]] = []
    self_path = Path(__file__).resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == self_path:
            continue
        if path.suffix not in SCAN_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            violations.append((path, 0, "non-utf8", "file is not UTF-8"))
            continue
        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(marker.lower() in lowered for marker in SAFE_CONTEXT_MARKERS):
                continue
            for term in BANNED_TERMS:
                if term.lower() in lowered:
                    violations.append((path, line_number, term, line.strip()))
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations = collect_violations(root)
    if violations:
        print("Release scan failed:")
        for path, line_number, term, line in violations:
            rel_path = path.relative_to(root)
            print(f"- {rel_path}:{line_number}: {term}: {line}")
        return 1
    print("Release scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
