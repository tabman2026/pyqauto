from __future__ import annotations

import json
import re
import sys
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any

EXPECTED_VERSION = "1.0.0rc2"
EXPECTED_WHEEL = f"pyqauto-{EXPECTED_VERSION}-py3-none-any.whl"
EXPECTED_SDIST = f"pyqauto-{EXPECTED_VERSION}.tar.gz"

FORBIDDEN_ENTRY_PARTS = {
    ".pypirc",
    "active.local",
    "local_reports",
    "logs",
    "source_router.db",
}

FORBIDDEN_TEXT_PATTERNS = [
    re.compile(("C:" + r"\\Users\\").encode("utf-8"), re.IGNORECASE),
    re.compile(("C:" + "/Users/").encode("utf-8"), re.IGNORECASE),
    re.compile(("/" + "Users" + r"/[^/\s]+/").encode("utf-8"), re.IGNORECASE),
    re.compile(rb"(TWINE_PASSWORD|PYPI_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9_./-]{8,}", re.IGNORECASE),
    re.compile(rb"pypi-[A-Za-z0-9_-]{20,}"),
]


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def _is_forbidden_entry(name: str) -> bool:
    parts = {part for part in Path(name).parts if part not in {".", ""}}
    return bool(parts.intersection(FORBIDDEN_ENTRY_PARTS))


def _scan_bytes(data: bytes, *, entry_name: str) -> str | None:
    if b"\x00" in data[:4096]:
        return None
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(data):
            return f"forbidden text pattern in {entry_name}"
    return None


def _wheel_metadata(path: Path) -> tuple[str | None, str | None, list[str], list[str]]:
    version = None
    console_scripts = None
    entries: list[str] = []
    findings: list[str] = []
    with zipfile.ZipFile(path) as zf:
        entries = zf.namelist()
        for entry in entries:
            if _is_forbidden_entry(entry):
                findings.append(f"forbidden entry {entry}")
            if entry.endswith(".dist-info/METADATA"):
                metadata = Parser().parsestr(zf.read(entry).decode("utf-8", errors="replace"))
                version = metadata.get("Version")
            if entry.endswith(".dist-info/entry_points.txt"):
                console_scripts = zf.read(entry).decode("utf-8", errors="replace")
            if entry.endswith((".py", ".txt", ".md", ".json", ".toml", ".yml", ".yaml", "PKG-INFO")):
                finding = _scan_bytes(zf.read(entry), entry_name=entry)
                if finding:
                    findings.append(finding)
    return version, console_scripts, entries, findings


def _sdist_metadata(path: Path) -> tuple[str | None, list[str], list[str]]:
    version = None
    entries: list[str] = []
    findings: list[str] = []
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            entries.append(member.name)
            if _is_forbidden_entry(member.name):
                findings.append(f"forbidden entry {member.name}")
            if not member.isfile():
                continue
            fileobj = tf.extractfile(member)
            if fileobj is None:
                continue
            data = fileobj.read()
            if member.name.endswith("PKG-INFO"):
                metadata = Parser().parsestr(data.decode("utf-8", errors="replace"))
                version = metadata.get("Version")
            if member.name.endswith((".py", ".txt", ".md", ".json", ".toml", ".yml", ".yaml", "PKG-INFO")):
                finding = _scan_bytes(data, entry_name=member.name)
                if finding:
                    findings.append(finding)
    return version, entries, findings


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dist_dir = Path(args[0]) if args else Path("dist")
    wheel = dist_dir / EXPECTED_WHEEL
    sdist = dist_dir / EXPECTED_SDIST

    checks: list[dict[str, Any]] = [
        _check("expected_wheel", wheel.exists(), EXPECTED_WHEEL),
        _check("expected_sdist", sdist.exists(), EXPECTED_SDIST),
    ]
    if not wheel.exists() or not sdist.exists():
        print(json.dumps({"status": "FAIL", "checks": checks}, ensure_ascii=False, indent=2))
        return 1

    wheel_version, entry_points, wheel_entries, wheel_findings = _wheel_metadata(wheel)
    sdist_version, sdist_entries, sdist_findings = _sdist_metadata(sdist)
    all_findings = wheel_findings + sdist_findings

    checks.extend(
        [
            _check("wheel_version", wheel_version == EXPECTED_VERSION, str(wheel_version)),
            _check("sdist_version", sdist_version == EXPECTED_VERSION, str(sdist_version)),
            _check(
                "cli_entry_point",
                entry_points is not None and "pyqauto = pyqauto.cli:main" in entry_points,
                "pyqauto console script points to pyqauto.cli:main",
            ),
            _check(
                "dual_namespace_packaged",
                any(entry.startswith("pyqauto/") for entry in wheel_entries)
                and any(entry.startswith("astock_source_router/") for entry in wheel_entries),
                "pyqauto and astock_source_router compatibility namespaces are packaged",
            ),
            _check(
                "no_forbidden_entries_or_text",
                not all_findings,
                "; ".join(all_findings[:5]) if all_findings else "clean",
            ),
            _check(
                "sdist_contains_release_notes",
                any(entry.endswith("RELEASE_NOTES_1.0.0rc2.md") for entry in sdist_entries),
                "rc2 release notes are included in sdist",
            ),
        ]
    )
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
