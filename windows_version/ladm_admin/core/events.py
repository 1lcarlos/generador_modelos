"""Comunicacion entre las operaciones del núcleo y quien las ejecuta (GUI o CLI).

Las operaciones nunca tocan widgets: informan su avance a traves de un
``Reporter`` y revisan un ``CancelToken`` para detenerse.
"""

from __future__ import annotations

import subprocess
import threading
from enum import Enum


class Level(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    COMMAND = "command"
    HEADER = "header"


class ItemStatus(str, Enum):
    PENDING = "pendiente"
    RUNNING = "en_proceso"
    OK = "ok"
    WARNING = "advertencia"
    ERROR = "error"
    SKIPPED = "omitido"
    CANCELLED = "cancelado"

    @property
    def label(self) -> str:
        return {
            ItemStatus.PENDING: "Pendiente",
            ItemStatus.RUNNING: "En proceso",
            ItemStatus.OK: "Correcto",
            ItemStatus.WARNING: "Con advertencias",
            ItemStatus.ERROR: "Error",
            ItemStatus.SKIPPED: "Omitido",
            ItemStatus.CANCELLED: "Cancelado",
        }[self]


class Reporter:
    """Receptor de eventos. La implementacion base no hace nada."""

    def log(self, message: str, level: Level = Level.INFO) -> None:  # pragma: no cover - interfaz
        pass

    def progress(self, done: int, total: int, text: str = "") -> None:  # pragma: no cover
        pass

    def item(self, key: str, status: ItemStatus, detail: str = "", **data) -> None:  # pragma: no cover
        pass


class ConsoleReporter(Reporter):
    """Reporter para línea de comandos."""

    _PREFIX = {
        Level.ERROR: "[ERROR] ",
        Level.WARNING: "[AVISO] ",
        Level.SUCCESS: "[OK]    ",
        Level.COMMAND: "$ ",
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, message: str, level: Level = Level.INFO) -> None:
        if level == Level.DEBUG and not self.verbose:
            return
        print(f"{self._PREFIX.get(level, '')}{message}", flush=True)

    def item(self, key: str, status: ItemStatus, detail: str = "", **data) -> None:
        if status not in (ItemStatus.PENDING, ItemStatus.RUNNING):
            print(f"  -> {key}: {status.label}{' - ' + detail if detail else ''}", flush=True)


class Cancelled(Exception):
    """Se lanza cuando el usuario detiene la operación."""


class CancelToken:
    """Permite detener una operación y el proceso externo que esté ejecutando."""

    def __init__(self):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            proc = self._process
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise Cancelled()

    def attach(self, process: subprocess.Popen | None) -> None:
        with self._lock:
            self._process = process
        if process is not None and self._event.is_set():
            self.cancel()
