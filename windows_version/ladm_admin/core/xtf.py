"""Lectura de archivos de transferencia XTF (INTERLIS 2.3 y 2.4).

- ``read_header``: rápido, solo lee la cabecera (modelos, emisor).
- ``scan_content``: recorre todo el archivo en streaming para contar baskets y
  objetos por clase (no carga el archivo en memoria).
- ``expand_sources``: convierte carpetas y ZIP en una lista de archivos .xtf.
"""

from __future__ import annotations

import hashlib
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .paths import work_dir

NS_ILI23 = "http://www.interlis.ch/INTERLIS2.3"
NS_ILI24 = "http://www.interlis.ch/xtf/2.4/INTERLIS"


@dataclass
class XtfModelRef:
    name: str
    version: str = ""


@dataclass
class XtfBasket:
    bid: str
    topic: str
    object_count: int = 0


@dataclass
class XtfInfo:
    path: Path
    interlis_version: str = ""
    sender: str = ""
    models: list[XtfModelRef] = field(default_factory=list)
    baskets: list[XtfBasket] = field(default_factory=list)
    class_counts: Counter = field(default_factory=Counter)
    error: str = ""
    source: Path | None = None  # ZIP de origen, si aplica

    @property
    def model_names(self) -> list[str]:
        return [m.name for m in self.models]

    @property
    def size_bytes(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    @property
    def total_objects(self) -> int:
        return sum(self.class_counts.values())


def _split(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


def read_header(path: str | Path) -> XtfInfo:
    """Lee solo la HEADERSECTION. No recorre los datos."""
    path = Path(path)
    info = XtfInfo(path=path)
    try:
        for event, elem in ET.iterparse(str(path), events=("start", "end")):
            ns, local = _split(elem.tag)
            low = local.lower()
            if event == "start" and low == "transfer":
                info.interlis_version = "2.4" if ns == NS_ILI24 else "2.3"
            elif event == "start" and low == "headersection":
                info.sender = elem.get("SENDER", "") or elem.get("sender", "")
            elif event == "end" and low == "model":
                if info.interlis_version == "2.4":
                    name = (elem.text or "").strip()
                    if name:
                        info.models.append(XtfModelRef(name))
                else:
                    info.models.append(XtfModelRef(elem.get("NAME", ""), elem.get("VERSION", "")))
            elif event == "end" and low == "sender" and info.interlis_version == "2.4":
                info.sender = (elem.text or "").strip()
            elif event == "end" and low == "headersection":
                break
            elif event == "start" and low == "datasection":
                break
    except ET.ParseError as exc:
        info.error = f"XML inválido: {exc}"
    except OSError as exc:
        info.error = f"No se pudo leer el archivo: {exc}"
    if not info.error and not info.models:
        info.error = "No se encontraron modelos en la cabecera (HEADERSECTION)"
    return info


def scan_content(path: str | Path, info: XtfInfo | None = None) -> XtfInfo:
    """Cuenta baskets y objetos por clase recorriendo el archivo en streaming."""
    path = Path(path)
    info = info or read_header(path)
    if info.error:
        return info
    info.baskets = []
    info.class_counts = Counter()
    depth = 0
    in_data = False
    current: XtfBasket | None = None
    try:
        context = ET.iterparse(str(path), events=("start", "end"))
        for event, elem in context:
            ns, local = _split(elem.tag)
            if event == "start":
                depth += 1
                if local.lower() == "datasection":
                    in_data = True
                    data_depth = depth
                elif in_data and depth == data_depth + 1:
                    bid = elem.get("BID") or elem.get(f"{{{NS_ILI24}}}bid") or ""
                    topic = local if info.interlis_version != "2.4" else f"{_model_from_ns(ns)}.{local}"
                    current = XtfBasket(bid=bid, topic=topic)
                    info.baskets.append(current)
                elif in_data and current is not None and depth == data_depth + 2:
                    if info.interlis_version == "2.4":
                        cls = f"{current.topic}.{local}"
                    else:
                        cls = local
                    info.class_counts[cls] += 1
                    current.object_count += 1
            else:
                if in_data and depth == data_depth + 1:
                    current = None
                    elem.clear()
                elif in_data and depth == data_depth + 2:
                    elem.clear()
                elif local.lower() == "datasection":
                    in_data = False
                depth -= 1
    except ET.ParseError as exc:
        info.error = f"XML inválido: {exc}"
    return info


def _model_from_ns(ns: str) -> str:
    # INTERLIS 2.4: http://www.interlis.ch/xtf/2.4/<Modelo>
    return ns.rstrip("/").rsplit("/", 1)[-1] if ns else ""


def _extract_zip(zip_path: Path) -> list[Path]:
    """Extrae los .xtf de un ZIP a la carpeta de trabajo y devuelve sus rutas."""
    stat = zip_path.stat()
    digest = hashlib.sha1(f"{zip_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:10]
    target = work_dir() / f"{zip_path.stem}_{digest}"
    result: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            if member.is_dir() or not member.filename.lower().endswith(".xtf"):
                continue
            name = Path(member.filename).name  # evita rutas peligrosas dentro del ZIP
            dest = target / name
            if not dest.exists() or dest.stat().st_size != member.file_size:
                target.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as out:
                    while chunk := src.read(1024 * 1024):
                        out.write(chunk)
            result.append(dest)
    return result


@dataclass
class SourceFile:
    """Archivo XTF a procesar y, si vino dentro de un ZIP, el ZIP de origen."""

    path: Path
    origin: Path | None = None

    @property
    def display(self) -> str:
        return f"{self.origin.name} > {self.path.name}" if self.origin else self.path.name


def expand_sources(paths: list[str | Path], recursive: bool = True, include_zip: bool = True) -> tuple[list[SourceFile], list[str]]:
    """Convierte archivos, carpetas y ZIP en una lista de .xtf (sin duplicados)."""
    found: list[SourceFile] = []
    errors: list[str] = []
    seen: set[Path] = set()

    def add(src: SourceFile) -> None:
        key = src.path.resolve()
        if key not in seen:
            seen.add(key)
            found.append(src)

    def handle_file(file: Path) -> None:
        suffix = file.suffix.lower()
        if suffix == ".xtf":
            add(SourceFile(file))
        elif suffix == ".zip" and include_zip:
            try:
                for xtf in _extract_zip(file):
                    add(SourceFile(xtf, origin=file))
            except (zipfile.BadZipFile, OSError) as exc:
                errors.append(f"{file.name}: ZIP no válido ({exc})")

    for raw in paths:
        p = Path(raw).resolve()
        if p.is_dir():
            iterator = p.rglob("*") if recursive else p.glob("*")
            for file in sorted(iterator):
                if file.is_file():
                    handle_file(file)
        elif p.is_file():
            handle_file(p)
        else:
            errors.append(f"No existe: {p}")
    return found, errors
