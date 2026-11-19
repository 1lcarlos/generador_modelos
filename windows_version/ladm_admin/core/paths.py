"""Ubicaciones de la aplicación y detección de herramientas externas."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .. import APP_SHORT

ILI2PG_VERSION = "5.5.1"
ILIVALIDATOR_VERSION = "1.15.0"


def base_dir() -> Path:
    """Carpeta raíz de la distribución (donde están ili2pg/, Modelos/, etc.)."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home())
    path = Path(root) / APP_SHORT
    path.mkdir(parents=True, exist_ok=True)
    return path


def work_dir() -> Path:
    """Carpeta para archivos temporales de trabajo (p.ej. ZIP extraidos)."""
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    path = Path(root) / APP_SHORT / "trabajo"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_log_dir() -> Path:
    return base_dir() / "log"


def default_ili2pg_jar() -> Path:
    return base_dir() / "ili2pg" / f"ili2pg-{ILI2PG_VERSION}" / f"ili2pg-{ILI2PG_VERSION}.jar"


def default_ilivalidator_jar() -> Path:
    return base_dir() / "ili2pg" / f"ilivalidator-{ILIVALIDATOR_VERSION}" / f"ilivalidator-{ILIVALIDATOR_VERSION}.jar"


def default_ctm12_script() -> Path:
    return base_dir() / "ctm12" / "insert_ctm12_pg.sql"


def find_java(configured: str | None = None) -> str | None:
    """Busca el ejecutable de Java: configurado > JRE incluido > JAVA_HOME > PATH."""
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    exe = "java.exe" if os.name == "nt" else "java"
    candidates.append(base_dir() / "jre" / "bin" / exe)
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin" / exe)
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    found = shutil.which("java")
    return found
