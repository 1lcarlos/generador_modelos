"""Ejecución de operaciones del núcleo en segundo plano.

Las operaciones corren en un hilo de Python; todo lo que llega a la interfaz
pasa por señales Qt (encoladas en el hilo principal), de modo que nunca se
tocan widgets desde el hilo de trabajo.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from ..core.events import ItemStatus, Level, Reporter


class QtReporter(QObject, Reporter):
    logged = Signal(str, str)                 # mensaje, nivel
    progressed = Signal(int, int, str)        # hechos, total, texto
    itemChanged = Signal(str, str, str, object)  # clave, estado, detalle, datos

    def log(self, message: str, level: Level = Level.INFO) -> None:
        self.logged.emit(message, level.value)

    def progress(self, done: int, total: int, text: str = "") -> None:
        self.progressed.emit(done, total, text)

    def item(self, key: str, status: ItemStatus, detail: str = "", **data) -> None:
        self.itemChanged.emit(key, status.value, detail, data)


@dataclass
class DecisionRequest:
    kind: str
    payload: Any
    result: Any = None
    event: threading.Event = field(default_factory=threading.Event)


class DecisionBridge(QObject):
    """Permite que el hilo de trabajo pregunte algo al usuario y espere la respuesta."""

    requested = Signal(object)

    def __init__(self):
        super().__init__()
        self._pending: list[DecisionRequest] = []

    def ask(self, kind: str, payload: Any, default: Any = None) -> Any:
        req = DecisionRequest(kind, payload, result=default)
        self._pending.append(req)
        self.requested.emit(req)
        req.event.wait()
        self._pending.remove(req)
        return req.result

    def release_all(self) -> None:
        """Libera preguntas pendientes (p.ej. al cerrar la ventana)."""
        for req in list(self._pending):
            req.event.set()


class Job(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, daemon=True, name="ladmadmin-job")
        self.thread.start()

    def _run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception:  # se informa en la interfaz
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(result)

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()
