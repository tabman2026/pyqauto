from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_cli(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "pyqauto.exe"
    return venv_dir / "bin" / "pyqauto"


def _run(command: list[str | os.PathLike[str]], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def test_installed_wheel_exposes_kline_cli(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    dist_dir = tmp_path / "dist"
    venv_dir = tmp_path / "venv"
    env = {**os.environ, "PYTHONUTF8": "1"}

    _run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            dist_dir,
        ],
        cwd=project_root,
        env=env,
    )
    wheels = sorted(dist_dir.glob("pyqauto-1.0.0rc2-py3-none-any.whl"))
    assert len(wheels) == 1

    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_dir)
    python = _venv_python(venv_dir)
    cli = _venv_cli(venv_dir)

    _run(
        [python, "-X", "utf8", "-m", "pip", "install", "--no-deps", wheels[0]],
        cwd=project_root,
        env=env,
    )
    assert cli.exists()

    for args in (
        ["--help"],
        ["kline", "--help"],
        ["kline", "000001", "--period", "15m", "--count", "10", "--help"],
        ["diagnose", "--json"],
        ["source-schema-probe-live", "--help"],
        ["probe-pytdx", "--help"],
    ):
        completed = _run([cli, *args], cwd=project_root, env=env)
        assert completed.returncode == 0
