"""Ejecución de herramientas Java (ili2pg, ilivalidator) sin shell y cancelable."""

from __future__ import annotations

import locale
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

from .events import CancelToken, Level, Reporter

_ERROR = re.compile(r"^\s*Error\b", re.I)
_WARNING = re.compile(r"^\s*Warning\b", re.I)
_PREFIX = re.compile(r"^(?:Error:\s*)+", re.I)
_PG_ERROR = re.compile(r"(?:ERROR|FATAL):\s+(.+)$")
_PG_NOISE = re.compile(r"transac|transaction is aborted", re.I)
_OBJECT_REF = re.compile(r"^Object \S+ at \(line", re.I)


def classify_line(line: str) -> Level:
    """ili2db/ilivalidator prefijan sus mensajes con 'Info:', 'Warning:' o 'Error:'."""
    if _ERROR.match(line):
        return Level.ERROR
    if _WARNING.match(line):
        return Level.WARNING
    if line.startswith("Exception") or line.startswith("\tat ") or "Exception:" in line[:80]:
        return Level.ERROR
    return Level.DEBUG


@dataclass
class ToolResult:
    returncode: int | None
    cancelled: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration: float = 0.0
    output_tail: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.cancelled and self.returncode == 0

    def main_error(self) -> str:
        """El mensaje de error más util: la causa reportada por PostgreSQL si existe."""
        candidates = self.errors or self.output_tail[-5:]
        for line in candidates:
            text = line.strip()
            m = _PG_ERROR.search(text)
            if m and not _PG_NOISE.search(m.group(1)):
                return m.group(1).strip()
        for line in candidates:
            text = _PREFIX.sub("", line.strip())
            if text and not _OBJECT_REF.match(text) and not text.startswith("failed to "):
                return text
        return _PREFIX.sub("", candidates[0].strip()) if candidates else ""

    def summary(self) -> str:
        if self.cancelled:
            return "Cancelado"
        if self.returncode == 0:
            return "Correcto" + (f" ({len(self.warnings)} advertencias)" if self.warnings else "")
        first = self.main_error()
        return f"Falló (código {self.returncode})" + (f": {first}" if first else "")


def mask_command(cmd: list[str], secrets: tuple[str, ...] = ("--dbpwd",)) -> str:
    shown = []
    hide_next = False
    for part in cmd:
        if hide_next:
            shown.append("****")
            hide_next = False
            continue
        shown.append(f'"{part}"' if " " in part else part)
        if part in secrets:
            hide_next = True
    return " ".join(shown)


def run_tool(
    cmd: list[str],
    reporter: Reporter,
    cancel: CancelToken | None = None,
    echo_level: Level = Level.DEBUG,
    max_kept_lines: int = 200,
) -> ToolResult:
    """Ejecuta el comando, transmite su salida al reporter y devuelve el resultado."""
    reporter.log(mask_command(cmd), Level.COMMAND)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    start = time.monotonic()
    result = ToolResult(returncode=None)
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        result.errors.append(f"No se encontró el ejecutable: {exc.filename or cmd[0]}")
        reporter.log(result.errors[-1], Level.ERROR)
        result.returncode = -1
        return result

    if cancel is not None:
        cancel.attach(process)
    try:
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip()
            if not line:
                continue
            level = classify_line(line)
            if level == Level.ERROR:
                result.errors.append(line.strip())
            elif level == Level.WARNING:
                result.warnings.append(line.strip())
            result.output_tail.append(line)
            if len(result.output_tail) > max_kept_lines:
                del result.output_tail[0]
            reporter.log(line, level if level in (Level.ERROR, Level.WARNING) else echo_level)
        process.wait()
    finally:
        if cancel is not None:
            cancel.attach(None)
            result.cancelled = cancel.cancelled
        if process.poll() is None:
            process.kill()
    result.returncode = process.returncode
    result.duration = time.monotonic() - start
    return result


def java_version(java: str) -> str | None:
    """Devuelve la versión de Java (p.ej. '1.8.0_221') o None si no se puede ejecutar."""
    try:
        out = subprocess.run(
            [java, "-version"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r'version "([^"]+)"', out.stderr + out.stdout)
    return match.group(1) if match else None
