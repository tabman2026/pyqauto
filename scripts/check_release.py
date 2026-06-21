"""Release leak scanner for pyqauto."""

from __future__ import annotations

from pathlib import Path

BANNED_TERMS = [
    "QMT",
    "XtQuantTrader",
    "xtdata",
    "券商",
    "真实交易",
    "候选股池",
    "买卖点",
    "收益率",
    "胜率",
    "webhook",
    "token",
    "cookie",
    "secret",
    "C:\\Users\\weibiaowei",
    "/Users/",
    "Desktop/CODEX",
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
    ".venv",
    ".venv_pyqauto_check",
    ".venv_pyqauto_v030_check",
    ".venv_pyqauto_031_check",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "local_reports",
}

SAFE_CONTEXT_MARKERS = [
    "do not",
    "does not",
    "never",
    "without",
    "no ",
    "not ",
    "not allowed",
    "not requested",
    "not used",
    "id-token",
    "trusted publishing",
    "forbidden",
    "redacted",
    "不提供",
    "不生成",
    "不接入",
    "不输出",
    "不保存",
    "不创建",
    "不允许",
    "未使用",
    "未要求",
    "否",
    "不发布",
    "不对外",
    "禁止",
    "严禁",
    "不得",
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
            safe_context = any(marker in lowered for marker in SAFE_CONTEXT_MARKERS)
            for term in BANNED_TERMS:
                if term.lower() in lowered and not safe_context:
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
