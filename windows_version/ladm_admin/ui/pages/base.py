"""Página base para operaciones: formulario arriba, resultados y registro abajo."""

from __future__ import annotations

from collections import Counter
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox, QScrollArea, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ...core.events import CancelToken, ItemStatus
from ..context import AppContext
from ..dialogs import ask_existing_schema, ask_import_conflict
from ..worker import DecisionBridge, DecisionRequest, Job, QtReporter
from ..widgets import LogView, ResultsTable, RunBar


class Page(QWidget):
    key = ""
    title = ""
    subtitle = ""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx

    def on_shown(self) -> None:
        """Se llama cada vez que la página se muestra."""

    def receive(self, payload: dict) -> None:
        """Recibe datos desde otra página (p.ej. archivos validados para importar)."""


class OperationPage(Page):
    run_text = "Ejecutar"
    run_icon = "play"

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(ctx, parent)
        self.job: Job | None = None
        self.cancel: CancelToken | None = None
        self.reporter = QtReporter()
        self.bridge = DecisionBridge()
        self._helper_jobs: list[Job] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        form_host = QWidget()
        self.form = QVBoxLayout(form_host)
        self.form.setContentsMargins(0, 0, 6, 0)
        self.form.setSpacing(12)
        scroll.setWidget(form_host)
        self.splitter.addWidget(scroll)

        self.tabs = QTabWidget()
        self.results = ResultsTable()
        self.log = LogView()
        self.tabs.addTab(self.results, "Resultados")
        self.tabs.addTab(self.log, "Registro")
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([760, 190])
        root.addWidget(self.splitter, 1)

        self.runbar = RunBar(self.run_text, self.run_icon)
        root.addWidget(self.runbar)

        self.reporter.logged.connect(self.log.append)
        self.reporter.progressed.connect(self.runbar.set_progress)
        self.reporter.itemChanged.connect(self.on_item)
        self.bridge.requested.connect(self._on_decision)
        self.runbar.runClicked.connect(self._on_run_clicked)
        self.runbar.stopClicked.connect(self.stop)
        self.ctx.busyChanged.connect(self._on_busy)

        self.build_form()
        self.form.addStretch(1)

    # ------------------------------------------------------ a implementar
    def build_form(self) -> None:
        raise NotImplementedError

    def start(self) -> None:
        """Valida el formulario y llama a run_job(...)."""
        raise NotImplementedError

    def on_results(self, results) -> None:
        """Hook opcional al terminar."""

    # ------------------------------------------------------------- trabajo
    def _on_run_clicked(self) -> None:
        if self.ctx.busy:
            QMessageBox.information(self, "Proceso en curso", "Espere a que termine el proceso actual.")
            return
        self.start()

    def run_job(self, fn: Callable, *args, items: list[tuple[str, str]] | None = None, **kwargs) -> None:
        self.cancel = CancelToken()
        self.results.reset(items or [])
        self.tabs.setCurrentWidget(self.results)
        self.log.clear()
        self.ctx.set_busy(True)
        self.runbar.set_running(True)
        top, bottom = self.splitter.sizes()
        if bottom < 0.4 * (top + bottom):   # dar espacio a resultados mientras se ejecuta
            total = top + bottom
            self.splitter.setSizes([int(total * 0.5), int(total * 0.5)])
        self.job = Job(fn, *args, self.reporter, self.cancel, **kwargs)
        self.job.finished.connect(self._on_finished)
        self.job.failed.connect(self._on_failed)
        self.job.start()

    def run_helper(self, fn: Callable, on_done: Callable, *args, on_error: Callable | None = None) -> Job:
        """Tarea corta en segundo plano (consultas a la BD, análisis) sin bloquear la interfaz."""
        job = Job(fn, *args)
        self._helper_jobs.append(job)

        def done(result):
            self._helper_jobs.remove(job)
            on_done(result)

        def failed(tb):
            self._helper_jobs.remove(job)
            if on_error:
                on_error(tb)
            else:
                QMessageBox.critical(self, "Error", tb.strip().splitlines()[-1])

        job.finished.connect(done)
        job.failed.connect(failed)
        job.start()
        return job

    def stop(self) -> None:
        if self.cancel and not self.cancel.cancelled:
            if QMessageBox.question(self, "Detener", "¿Detener el proceso en curso?") == QMessageBox.Yes:
                self.cancel.cancel()
                self.runbar.status.setText("Deteniendo...")
                self.bridge.release_all()

    def on_item(self, key: str, status: str, detail: str, data: dict) -> None:
        self.results.update_item(key, status, detail, data)

    def _on_finished(self, results) -> None:
        self.ctx.set_busy(False)
        counts = Counter(r.status for r in results or [])
        parts = [f"{counts[s]} {s.label.lower()}" for s in ItemStatus if counts[s]]
        self.runbar.finish("Finalizado: " + (", ".join(parts) if parts else "sin elementos"))
        if counts[ItemStatus.ERROR]:
            self.runbar.status.setStyleSheet("color: #c0352b; font-weight: 600;")
        else:
            self.runbar.status.setStyleSheet("")
        self.on_results(results)

    def _on_failed(self, tb: str) -> None:
        self.ctx.set_busy(False)
        self.runbar.finish("El proceso terminó con un error inesperado")
        self.log.append(tb, "error")
        self.tabs.setCurrentWidget(self.log)
        QMessageBox.critical(self, "Error inesperado", tb.strip().splitlines()[-1])

    def _on_busy(self, busy: bool) -> None:
        if not (self.job and self.job.is_running()):
            self.runbar.run_btn.setEnabled(not busy)

    def _on_decision(self, req: DecisionRequest) -> None:
        try:
            if req.kind == "existing_schema":
                req.result = ask_existing_schema(req.payload, self)
            elif req.kind == "import_conflict":
                req.result = ask_import_conflict(req.payload, self)
        finally:
            req.event.set()

    def shutdown(self) -> None:
        if self.cancel:
            self.cancel.cancel()
        self.bridge.release_all()
