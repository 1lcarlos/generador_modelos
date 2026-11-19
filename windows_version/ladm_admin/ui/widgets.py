"""Componentes reutilizables de la interfaz."""

from __future__ import annotations

import html
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QToolButton,
    QVBoxLayout, QWidget,
)

from ..core.events import ItemStatus, Level
from . import theme
from .icons import dot, icon


# ------------------------------------------------------------------ utilidades
def button(text: str, icon_name: str | None = None, variant: str | None = None, tooltip: str = "") -> QPushButton:
    b = QPushButton(text)
    if icon_name:
        color = theme.tokens().primary_text if variant == "primary" else theme.tokens().text_muted
        b.setIcon(icon(icon_name, color))
    if variant:
        b.setProperty("variant", variant)
    if tooltip:
        b.setToolTip(tooltip)
    b.setCursor(Qt.PointingHandCursor)
    return b


def label(text: str, name: str | None = None, wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


def hint(text: str) -> QLabel:
    lbl = label(text, "Hint", wrap=True)
    lbl.setTextFormat(Qt.RichText)
    lbl.setOpenExternalLinks(False)
    return lbl


def open_path(path: str | Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_in_explorer(path: str | Path) -> None:
    p = Path(path)
    if os.name == "nt" and p.exists():
        subprocess.Popen(["explorer", "/select,", str(p)])
    else:
        open_path(p.parent if p.is_file() else p)


def status_color(status: ItemStatus | str) -> str:
    t = theme.tokens()
    status = ItemStatus(status)
    return {
        ItemStatus.OK: t.success, ItemStatus.WARNING: t.warning, ItemStatus.ERROR: t.error,
        ItemStatus.RUNNING: t.info, ItemStatus.SKIPPED: t.text_muted, ItemStatus.CANCELLED: t.text_muted,
        ItemStatus.PENDING: t.border,
    }[status]


def status_item(status: ItemStatus | str, text: str | None = None) -> QTableWidgetItem:
    status = ItemStatus(status)
    item = QTableWidgetItem(dot(status_color(status)), text or status.label)
    item.setData(Qt.UserRole, status.value)
    return item


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def duration_text(seconds: float | None) -> str:
    if not seconds:
        return ""
    m, s = divmod(int(round(seconds)), 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


# ----------------------------------------------------------------- contenedores
class Card(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None, step: int | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 14, 18, 16)
        self.body.setSpacing(10)
        if title:
            head = QHBoxLayout()
            head.setSpacing(10)
            if step is not None:
                head.addWidget(label(str(step), "StepNumber"))
            col = QVBoxLayout()
            col.setSpacing(1)
            col.addWidget(label(title, "CardTitle"))
            if subtitle:
                col.addWidget(hint(subtitle))
            head.addLayout(col, 1)
            self.header_tools = QHBoxLayout()
            self.header_tools.setSpacing(6)
            head.addLayout(self.header_tools)
            self.body.addLayout(head)


class Banner(QFrame):
    def __init__(self, kind: str = "info", text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Banner")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        self._icon = QLabel()
        self._text = label("", wrap=True)
        self._text.setTextFormat(Qt.RichText)
        self._text.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self._text.setOpenExternalLinks(True)
        lay.addWidget(self._icon, 0, Qt.AlignTop)
        lay.addWidget(self._text, 1)
        self.action = button("", variant="link")
        self.action.hide()
        lay.addWidget(self.action, 0, Qt.AlignTop)
        self.set(kind, text)

    def set(self, kind: str, text: str) -> None:
        t = theme.tokens()
        color = {"warning": t.warning, "error": t.error, "success": t.success}.get(kind, t.info)
        name = {"warning": "alert", "error": "alert", "success": "check"}.get(kind, "info")
        self.setProperty("kind", kind)
        self._icon.setPixmap(icon(name, color).pixmap(18, 18))
        self._text.setText(text)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(bool(text))


class Collapsible(QWidget):
    def __init__(self, title: str, expanded: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.toggle.setStyleSheet("QToolButton { font-weight: 600; padding: 4px 2px; }")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(18, 0, 0, 0)
        self.content.setVisible(expanded)
        self.toggle.toggled.connect(self._on_toggle)
        lay.addWidget(self.toggle, 0, Qt.AlignLeft)
        lay.addWidget(self.content)

    def _on_toggle(self, checked: bool) -> None:
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content.setVisible(checked)


# ---------------------------------------------------------------- entradas
class PathEdit(QWidget):
    changed = Signal(str)

    def __init__(self, mode: str = "file", file_filter: str = "", placeholder: str = "",
                 dialog_title: str = "Seleccionar", parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = mode
        self.file_filter = file_filter
        self.dialog_title = dialog_title
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.editingFinished.connect(lambda: self.changed.emit(self.text()))
        browse = QToolButton()
        browse.setIcon(icon("folder" if mode == "dir" else "file", theme.tokens().text_muted))
        browse.setToolTip("Examinar...")
        browse.setCursor(Qt.PointingHandCursor)
        browse.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(browse)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(value or "")

    def _browse(self) -> None:
        start = self.text() or str(Path.home())
        if self.mode == "dir":
            path = QFileDialog.getExistingDirectory(self, self.dialog_title, start)
        elif self.mode == "save":
            path, _ = QFileDialog.getSaveFileName(self, self.dialog_title, start, self.file_filter)
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.dialog_title, start, self.file_filter)
        if path:
            self.setText(str(Path(path)))
            self.changed.emit(self.text())


class DropArea(QFrame):
    """Zona para agregar archivos/carpetas con botones o arrastrando."""

    pathsAdded = Signal(list)

    def __init__(self, text: str, file_filter: str = "Transferencias INTERLIS (*.xtf *.zip)",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.file_filter = file_filter
        self.setAcceptDrops(True)
        self.setObjectName("DropArea")
        t = theme.tokens()
        self._base_style = (f"QFrame#DropArea {{ border: 1.5px dashed {t.border}; border-radius: 8px; "
                            f"background: {t.surface_alt}; }}")
        self.setStyleSheet(self._base_style)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        ic = QLabel()
        ic.setPixmap(icon("import", t.text_muted).pixmap(22, 22))
        lay.addWidget(ic)
        lay.addWidget(label(text, "Muted", wrap=True), 1)
        self.btn_files = button("Agregar archivos", "file")
        self.btn_dir = button("Agregar carpeta", "folder")
        self.btn_files.clicked.connect(self._add_files)
        self.btn_dir.clicked.connect(self._add_dir)
        lay.addWidget(self.btn_files)
        lay.addWidget(self.btn_dir)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos", str(Path.home()), self.file_filter)
        if files:
            self.pathsAdded.emit(files)

    def _add_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta (se busca en subcarpetas)", str(Path.home()))
        if folder:
            self.pathsAdded.emit([folder])

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._base_style.replace("dashed", "solid"))

    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet(self._base_style)

    def dropEvent(self, event) -> None:
        self.setStyleSheet(self._base_style)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.pathsAdded.emit(paths)


# ------------------------------------------------------------------- tablas
class DataTable(QTableWidget):
    """Tabla de solo lectura con estilo uniforme y menú contextual configurable."""

    def __init__(self, headers: list[str], stretch_col: int | None = None, parent: QWidget | None = None):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().setDefaultSectionSize(30)
        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(stretch_col is None)
        if stretch_col is not None:
            hh.setSectionResizeMode(stretch_col, QHeaderView.Stretch)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.menu_builder = None  # callable(row:int, menú:QMenu)

    def _menu(self, pos) -> None:
        row = self.rowAt(pos.y())
        if row < 0 or self.menu_builder is None:
            return
        menu = QMenu(self)
        self.menu_builder(row, menu)
        if not menu.isEmpty():
            menu.exec(self.viewport().mapToGlobal(pos))

    def set_text(self, row: int, col: int, text: str, tooltip: str | None = None, data=None) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if tooltip:
            item.setToolTip(tooltip)
        if data is not None:
            item.setData(Qt.UserRole, data)
        self.setItem(row, col, item)
        return item


class ResultsTable(DataTable):
    """Resultados por elemento: estado, detalle, duracion y accesos al log/salida."""

    COLS = ["Elemento", "Estado", "Detalle", "Duración"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(self.COLS, stretch_col=2, parent=parent)
        self.setColumnWidth(0, 220)
        self.setColumnWidth(1, 140)
        self.setColumnWidth(3, 90)
        self._rows: dict[str, int] = {}
        self._data: dict[str, dict] = {}
        self.menu_builder = self._build_menu
        self.doubleClicked.connect(lambda idx: self._open_log(idx.row()))

    def reset(self, keys: list[tuple[str, str]]) -> None:
        """keys: (clave, texto visible)."""
        self.setRowCount(0)
        self._rows.clear()
        self._data.clear()
        for key, text in keys:
            r = self.rowCount()
            self.insertRow(r)
            self._rows[key] = r
            self.set_text(r, 0, text, tooltip=key)
            self.setItem(r, 1, status_item(ItemStatus.PENDING))

    def update_item(self, key: str, status: str, detail: str, data: dict) -> None:
        r = self._rows.get(key)
        if r is None:
            r = self.rowCount()
            self.insertRow(r)
            self._rows[key] = r
            self.set_text(r, 0, Path(key).name or key, tooltip=key)
        self.setItem(r, 1, status_item(status))
        if detail or status != ItemStatus.RUNNING.value:
            self.set_text(r, 2, detail, tooltip=detail)
        if data.get("duration"):
            self.set_text(r, 3, duration_text(data["duration"]))
        self._data.setdefault(key, {}).update(data)
        if status == ItemStatus.RUNNING.value:
            self.scrollToItem(self.item(r, 0))

    def key_at(self, row: int) -> str | None:
        return next((k for k, r in self._rows.items() if r == row), None)

    def data_for(self, row: int) -> dict:
        key = self.key_at(row)
        return self._data.get(key, {}) if key else {}

    def _open_log(self, row: int) -> None:
        log = self.data_for(row).get("log_file")
        if log and Path(log).exists():
            open_path(log)

    def _build_menu(self, row: int, menu: QMenu) -> None:
        data = self.data_for(row)
        if data.get("log_file"):
            menu.addAction(icon("log"), "Abrir log", lambda: open_path(data["log_file"]))
        if data.get("output_file"):
            menu.addAction(icon("folder"), "Mostrar archivo generado", lambda: reveal_in_explorer(data["output_file"]))
        menu.addAction(icon("copy"), "Copiar detalle",
                       lambda: QGuiApplication.clipboard().setText(self.item(row, 2).text() if self.item(row, 2) else ""))


# --------------------------------------------------------------------- log
_LOG_LEVELS = {
    "Resumen": {Level.INFO, Level.SUCCESS, Level.WARNING, Level.ERROR, Level.HEADER},
    "Detallado": set(Level),
    "Advertencias y errores": {Level.WARNING, Level.ERROR},
    "Solo errores": {Level.ERROR},
}


class LogView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        bar = QHBoxLayout()
        bar.addWidget(label("Mostrar:", "Muted"))
        self.filter = QComboBox()
        self.filter.addItems(list(_LOG_LEVELS))
        self.filter.currentTextChanged.connect(self._rerender)
        bar.addWidget(self.filter)
        self.counter = label("", "Muted")
        bar.addWidget(self.counter)
        bar.addStretch(1)
        for text, ic, fn in (("Copiar", "copy", self._copy), ("Guardar...", "file", self._save),
                             ("Limpiar", "trash", self.clear)):
            b = QToolButton()
            b.setIcon(icon(ic, theme.tokens().text_muted))
            b.setToolTip(text)
            b.clicked.connect(fn)
            bar.addWidget(b)
        lay.addLayout(bar)
        self.view = QPlainTextEdit()
        self.view.setObjectName("Log")
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(30000)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        lay.addWidget(self.view, 1)
        self._entries: list[tuple[str, Level, str]] = []
        self._pending: list[tuple[str, Level, str]] = []
        self._errors = 0
        self._warnings = 0
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._flush)
        self._timer.start()

    def append(self, message: str, level: str | Level = Level.INFO) -> None:
        level = Level(level)
        entry = (datetime.now().strftime("%H:%M:%S"), level, message)
        self._entries.append(entry)
        if len(self._entries) > 60000:
            del self._entries[:10000]
        if level == Level.ERROR:
            self._errors += 1
        elif level == Level.WARNING:
            self._warnings += 1
        if level in _LOG_LEVELS[self.filter.currentText()]:
            self._pending.append(entry)

    def _html(self, entry) -> str:
        t = theme.tokens()
        ts, level, msg = entry
        color = {Level.ERROR: t.error, Level.WARNING: t.warning, Level.SUCCESS: t.success,
                 Level.COMMAND: t.info, Level.DEBUG: t.text_muted, Level.HEADER: t.text}.get(level, t.log_text)
        weight = "font-weight:600;" if level in (Level.HEADER, Level.SUCCESS, Level.ERROR) else ""
        text = html.escape(msg)
        if level == Level.HEADER:
            text = f"━━ {text} ━━"
        return (f'<span style="color:{t.text_muted}">{ts}</span>&nbsp;&nbsp;'
                f'<span style="color:{color};{weight}">{text}</span>')

    def _flush(self) -> None:
        if not self._pending:
            return
        chunk = "<br>".join(self._html(e) for e in self._pending)
        self._pending.clear()
        at_bottom = self.view.verticalScrollBar().value() >= self.view.verticalScrollBar().maximum() - 4
        self.view.appendHtml(chunk)
        if at_bottom:
            self.view.moveCursor(QTextCursor.End)
            self.view.ensureCursorVisible()
        self.counter.setText(f"{self._errors} errores, {self._warnings} advertencias" if self._errors or self._warnings else "")

    def _rerender(self) -> None:
        allowed = _LOG_LEVELS[self.filter.currentText()]
        self._pending.clear()
        self.view.clear()
        shown = [e for e in self._entries if e[1] in allowed][-20000:]
        for i in range(0, len(shown), 2000):
            self.view.appendHtml("<br>".join(self._html(e) for e in shown[i:i + 2000]))

    def clear(self) -> None:
        self._entries.clear()
        self._pending.clear()
        self._errors = self._warnings = 0
        self.view.clear()
        self.counter.setText("")

    def plain_text(self) -> str:
        return "\n".join(f"{ts} [{lvl.value.upper():7}] {msg}" for ts, lvl, msg in self._entries)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.plain_text())

    def _save(self) -> None:
        name = f"registro_{datetime.now():%Y%m%d_%H%M%S}.log"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar registro", str(Path.home() / name),
                                              "Registro (*.log *.txt)")
        if path:
            Path(path).write_text(self.plain_text(), encoding="utf-8")


# ------------------------------------------------------------ barra de ejecución
class RunBar(QFrame):
    """Boton principal, detener y progreso. Comun a todas las operaciones."""

    runClicked = Signal()
    stopClicked = Signal()

    def __init__(self, run_text: str, run_icon: str = "play", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(4)
        self.status = label("Listo", "Muted")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        col.addWidget(self.status)
        col.addWidget(self.bar)
        lay.addLayout(col, 1)
        self.stop_btn = button("Detener", "stop", "danger")
        self.stop_btn.setEnabled(False)
        self.run_btn = button(run_text, run_icon, "primary")
        self.run_btn.setMinimumWidth(170)
        lay.addWidget(self.stop_btn)
        lay.addWidget(self.run_btn)
        self.run_btn.clicked.connect(self.runClicked)
        self.stop_btn.clicked.connect(self.stopClicked)

    def set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        if running:
            self.bar.setRange(0, 0)  # indeterminado hasta el primer avance
            self.status.setText("Iniciando...")

    def set_progress(self, done: int, total: int, text: str) -> None:
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(done)
        if text:
            self.status.setText(f"{text}  ({min(done + 1, total)}/{total})" if done < total else text)

    def finish(self, text: str) -> None:
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.status.setText(text)
        self.set_running(False)
        self.status.setText(text)
