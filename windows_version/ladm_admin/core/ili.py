"""Lectura liviana de archivos de modelo INTERLIS (.ili).

No reemplaza al compilador ili2c: solo extrae nombre, version e IMPORTS de cada
MODEL para poder ofrecer la lista de modelos y sugerir cuales seleccionar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"!!.*?$", re.M)
_MODEL = re.compile(
    r"^\s*(?P<kind>(?:(?:CONTRACTED|TYPE|REFSYSTEM|SYMBOLOGY)\s+)*)MODEL\s+(?P<name>[A-Za-z_][\w]*)"
    r"(?P<rest>[^=]*)=",
    re.M,
)
_VERSION = re.compile(r'VERSION\s+"([^"]*)"')
_IMPORTS = re.compile(r"\bIMPORTS\s+([^;]*);")
_END_MODEL = r"^\s*END\s+{name}\s*\."
_ILI_VERSION = re.compile(r"^\s*INTERLIS\s+(\d+\.\d+)\s*;", re.M)

BUILTIN_MODELS = {"INTERLIS"}


@dataclass
class IliModel:
    name: str
    file: Path
    kind: str = ""  # "", CONTRACTED, TYPE, REFSYSTEM, SYMBOLOGY
    version: str = ""
    ili_version: str = ""
    imports: list[str] = field(default_factory=list)

    @property
    def is_base(self) -> bool:
        """Modelos de tipos/sistemas de referencia: no contienen datos propios."""
        return self.kind in ("TYPE", "REFSYSTEM", "SYMBOLOGY")


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_ili_file(path: str | Path) -> list[IliModel]:
    path = Path(path)
    text = _read_text(path)
    text = _BLOCK_COMMENT.sub(" ", text)
    text = _LINE_COMMENT.sub("", text)
    ili_version_match = _ILI_VERSION.search(text)
    ili_version = ili_version_match.group(1) if ili_version_match else ""

    models: list[IliModel] = []
    for match in _MODEL.finditer(text):
        name = match.group("name")
        kinds = (match.group("kind") or "").split()
        kind = next((k for k in kinds if k != "CONTRACTED"), "CONTRACTED" if kinds else "")
        start = match.end()
        end_match = re.search(_END_MODEL.format(name=re.escape(name)), text[start:], re.M)
        body = text[start : start + end_match.start()] if end_match else text[start:]
        version_match = _VERSION.search(match.group("rest"))
        imports: list[str] = []
        # Los IMPORTS van al inicio del modelo; basta con revisar la cabecera.
        for imp in _IMPORTS.finditer(body[:5000]):
            for token in imp.group(1).replace("\n", " ").split(","):
                token = token.strip()
                if token.upper().startswith("UNQUALIFIED "):
                    token = token[len("UNQUALIFIED "):].strip()
                if token and token not in BUILTIN_MODELS and token not in imports:
                    imports.append(token)
        models.append(
            IliModel(
                name=name,
                file=path,
                kind=kind,
                version=version_match.group(1) if version_match else "",
                ili_version=ili_version,
                imports=imports,
            )
        )
    return models


def scan_model_dir(folder: str | Path, recursive: bool = False) -> list[IliModel]:
    """Devuelve todos los modelos definidos en los .ili de una carpeta."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    pattern = "**/*.ili" if recursive else "*.ili"
    result: list[IliModel] = []
    for file in sorted(folder.glob(pattern)):
        try:
            result.extend(parse_ili_file(file))
        except OSError:
            continue
    return result


def suggested_models(models: list[IliModel]) -> list[str]:
    """Modelos a pasar en --models al crear el esquema.

    ili2pg solo crea tablas para los TOPICs de los modelos indicados (los
    importados se registran pero sin tablas), por eso se sugieren todos los
    modelos con contenido propio, excluyendo los de tipos (TYPE/REFSYSTEM).
    """
    return list(dict.fromkeys(m.name for m in models if not m.is_base))


def duplicate_models(models: list[IliModel]) -> dict[str, list[Path]]:
    """Modelos definidos en más de un archivo (ili2c podria tomar cualquiera)."""
    by_name: dict[str, list[Path]] = {}
    for m in models:
        by_name.setdefault(m.name, []).append(m.file)
    return {name: files for name, files in by_name.items() if len(files) > 1}


def dependency_closure(selected: list[str], models: list[IliModel]) -> list[str]:
    """Modelos seleccionados más todas sus dependencias conocidas."""
    by_name = {m.name: m for m in models}
    result: list[str] = []

    def visit(name: str) -> None:
        if name in result:
            return
        for dep in by_name.get(name, IliModel(name, Path())).imports:
            visit(dep)
        result.append(name)

    for name in selected:
        visit(name)
    return result
