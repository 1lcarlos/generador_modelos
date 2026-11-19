"""Pruebas del instalador de herramientas (sin red)."""

import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ladm_admin.core import tools_setup  # noqa: E402
from ladm_admin.core.tools_setup import ToolPackage, ToolSetupError, install_from_zip  # noqa: E402


def _make_zip(path: Path, jar_name: str, extra: dict | None = None) -> str:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(jar_name, b"jar")
        zf.writestr("libs/dep.jar", b"dep")
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_setup.paths, "base_dir", lambda: tmp_path)
    return tmp_path


def test_install_from_zip_ok(base, tmp_path):
    z = tmp_path / "t.zip"
    digest = _make_zip(z, "herr-1.0.jar")
    pkg = ToolPackage("herr", "1.0", "http://x", digest)
    assert not pkg.installed()
    jar = install_from_zip(pkg, z)
    assert jar.is_file() and pkg.installed()


def test_install_rejects_wrong_checksum(base, tmp_path):
    z = tmp_path / "t.zip"
    _make_zip(z, "herr-1.0.jar")
    pkg = ToolPackage("herr", "1.0", "http://x", "0" * 64)
    with pytest.raises(ToolSetupError, match="SHA-256"):
        install_from_zip(pkg, z)
    assert not pkg.folder.exists()


def test_install_rejects_path_traversal(base, tmp_path):
    z = tmp_path / "t.zip"
    digest = _make_zip(z, "herr-1.0.jar", {"../fuera.txt": b"x"})
    with pytest.raises(ToolSetupError, match="no permitida"):
        install_from_zip(ToolPackage("herr", "1.0", "http://x", digest), z)


def test_pinned_versions_match_paths():
    names = {p.name: p for p in tools_setup.PACKAGES}
    assert names["ili2pg"].version == tools_setup.paths.ILI2PG_VERSION
    assert names["ilivalidator"].jar.name == f"ilivalidator-{tools_setup.paths.ILIVALIDATOR_VERSION}.jar"
    assert all(len(p.sha256) == 64 for p in tools_setup.PACKAGES)
