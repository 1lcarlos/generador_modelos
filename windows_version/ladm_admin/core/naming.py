"""Convenciones de nombres: municipio <-> esquema <-> dataset <-> carpeta."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_DIVIPOLA = re.compile(r"(?<!\d)(\d{5})(?!\d)")
_VALID_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


class StorageMode(str, Enum):
    """Como se organizan los municipios en la base de datos."""

    PER_MUNICIPALITY = "por_municipio"   # un esquema por municipio (cun25279)
    SHARED = "esquema_unico"             # un esquema con un dataset por municipio

    @property
    def label(self) -> str:
        return {
            StorageMode.PER_MUNICIPALITY: "Un esquema por municipio",
            StorageMode.SHARED: "Esquema único con datasets por municipio",
        }[self]


@dataclass
class NamingConvention:
    schema_prefix: str = "cun"

    def schema_for_code(self, code: str) -> str:
        return f"{self.schema_prefix}{code}".lower()

    def code_for_schema(self, schema: str) -> str:
        if self.schema_prefix and schema.lower().startswith(self.schema_prefix.lower()):
            return schema[len(self.schema_prefix):]
        return schema


def code_from_path(path: str | Path, origin: str | Path | None = None) -> str | None:
    """Detecta el código DIVIPOLA (5 dígitos) en el nombre del archivo o sus carpetas."""
    candidates: list[str] = []
    p = Path(path)
    candidates.append(p.stem)
    if origin is not None:
        candidates.append(Path(origin).stem)
        candidates.extend(part for part in reversed(Path(origin).parent.parts[-3:]))
    candidates.extend(part for part in reversed(p.parent.parts[-3:]))
    for text in candidates:
        match = _DIVIPOLA.search(text)
        if match:
            return match.group(1)
    return None


def validate_identifier(name: str) -> str | None:
    """Devuelve un mensaje de error si el nombre no es un identificador PostgreSQL seguro."""
    if not name:
        return "El nombre está vacío"
    if len(name) > 63:
        return "El nombre supera 63 caracteres"
    if not _VALID_IDENT.match(name):
        return "Use solo minúsculas, números y guion bajo, sin iniciar con número"
    return None
