"""Descarga e instalación de ili2pg e ilivalidator (no se versionan en git).

Las versiones están fijadas y cada archivo se verifica con su huella SHA-256
antes de extraerlo en ``ili2pg/<herramienta>-<versión>/``.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import paths


@dataclass(frozen=True)
class ToolPackage:
    name: str
    version: str
    url: str
    sha256: str

    @property
    def folder(self) -> Path:
        return paths.base_dir() / "ili2pg" / f"{self.name}-{self.version}"

    @property
    def jar(self) -> Path:
        return self.folder / f"{self.name}-{self.version}.jar"

    def installed(self) -> bool:
        return self.jar.is_file() and (self.folder / "libs").is_dir()


PACKAGES = [
    ToolPackage("ili2pg", paths.ILI2PG_VERSION,
                f"https://downloads.interlis.ch/ili2pg/ili2pg-{paths.ILI2PG_VERSION}.zip",
                "770f603acb183c7c676fc99047c87a56f33187c70090d17d8c485a85218c048e"),
    ToolPackage("ilivalidator", paths.ILIVALIDATOR_VERSION,
                f"https://downloads.interlis.ch/ilivalidator/ilivalidator-{paths.ILIVALIDATOR_VERSION}.zip",
                "df7ee8961743e3dfc586f646af4f63d49dabf920e98a4836a32edf676d0b20c7"),
]


class ToolSetupError(Exception):
    pass


def missing_packages() -> list[ToolPackage]:
    return [p for p in PACKAGES if not p.installed()]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def install_from_zip(pkg: ToolPackage, zip_path: Path, verify: bool = True) -> Path:
    """Verifica la huella del ZIP y lo extrae en la carpeta de la herramienta."""
    if verify:
        digest = _sha256(zip_path)
        if digest != pkg.sha256:
            raise ToolSetupError(f"La huella SHA-256 de {zip_path.name} no coincide (archivo dañado o alterado)")
    target = pkg.folder
    tmp = target.with_name(target.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            dest = (tmp / member.filename).resolve()
            if not str(dest).startswith(str(tmp.resolve())):
                raise ToolSetupError(f"Ruta no permitida dentro del ZIP: {member.filename}")
        zf.extractall(tmp)
    if not (tmp / pkg.jar.name).is_file():
        shutil.rmtree(tmp, ignore_errors=True)
        raise ToolSetupError(f"El ZIP no contiene {pkg.jar.name}")
    shutil.rmtree(target, ignore_errors=True)
    tmp.rename(target)
    return pkg.jar


def download_and_install(pkg: ToolPackage, progress: Callable[[str, int, int], None] | None = None,
                         timeout: int = 60) -> Path:
    """Descarga el ZIP oficial, lo verifica y lo instala."""
    with tempfile.TemporaryDirectory(prefix="ladmadmin_") as tmpdir:
        zip_path = Path(tmpdir) / f"{pkg.name}-{pkg.version}.zip"
        req = urllib.request.Request(pkg.url, headers={"User-Agent": "LADMAdmin"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(zip_path, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while chunk := resp.read(256 * 1024):
                    out.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(pkg.name, done, total)
        except OSError as exc:
            raise ToolSetupError(f"No se pudo descargar {pkg.url}: {exc}") from exc
        return install_from_zip(pkg, zip_path)


def install_missing(progress: Callable[[str, int, int], None] | None = None,
                    log: Callable[[str], None] = print) -> list[Path]:
    installed = []
    for pkg in missing_packages():
        log(f"Descargando {pkg.name} {pkg.version} desde {pkg.url} ...")
        installed.append(download_and_install(pkg, progress))
        log(f"  instalado en {pkg.folder}")
    if not installed:
        log("ili2pg e ilivalidator ya están instalados.")
    return installed
