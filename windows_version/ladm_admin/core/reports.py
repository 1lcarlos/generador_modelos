"""Lectura de reportes de validación y exportación de resultados."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .operations import ItemResult


@dataclass
class ValidationIssue:
    type: str          # Error | Warning
    message: str
    class_name: str = ""
    tid: str = ""
    line: str = ""
    x: str = ""
    y: str = ""


def read_validation_csv(path: str | Path, include_warnings: bool = True) -> list[ValidationIssue]:
    """Lee el --csvlog de ilivalidator y devuelve solo errores (y advertencias)."""
    path = Path(path)
    if not path.is_file():
        return []
    wanted = {"Error"} | ({"Warning"} if include_warnings else set())
    issues: list[ValidationIssue] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            kind = (row.get("Type") or "").strip()
            if kind not in wanted:
                continue
            issues.append(ValidationIssue(
                type=kind,
                message=(row.get("Message") or "").strip(),
                class_name=(row.get("IliQName") or row.get("ObjTag") or "").strip(),
                tid=(row.get("Tid") or "").strip(),
                line=(row.get("Line") or "").strip(),
                x=(row.get("Geometry_x") or "").strip(),
                y=(row.get("Geometry_y") or "").strip(),
            ))
    return issues


def write_results_csv(results: list[ItemResult], path: str | Path) -> None:
    """Guarda el resumen de una operación (para adjuntar a informes)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["Elemento", "Estado", "Detalle", "Errores", "Advertencias",
                         "Duración (s)", "Log", "Salida"])
        for r in results:
            writer.writerow([r.key, r.status.label, r.detail, r.errors, r.warnings,
                             f"{r.duration:.1f}", r.log_file, r.output_file])
