from __future__ import annotations

from pathlib import Path


def test_publish_workflow_is_gated_by_test_and_build() -> None:
    text = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "  test:" in text
    assert "  build:" in text
    assert "  publish:" in text
    assert "needs: test" in text
    assert "needs: build" in text
    assert "python -X utf8 -m pytest -q" in text
    assert "python -X utf8 -m ruff check ." in text
    assert "python -X utf8 scripts/check_release.py" in text
    assert "python -X utf8 -m twine check dist/*" in text
    assert "python -X utf8 scripts/check_dist_contents.py dist" in text
    assert "id-token: write" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text


def test_publish_workflow_does_not_use_password_or_local_upload() -> None:
    text = Path(".github/workflows/publish.yml").read_text(encoding="utf-8").lower()

    assert "twine upload" not in text
    assert "twine_password" not in text
    assert "pypi_token" not in text
    assert "password:" not in text
    assert "username:" not in text
    assert "secrets." not in text
