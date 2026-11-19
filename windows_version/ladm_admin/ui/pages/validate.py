"""Paso 1: validar archivos XTF con ilivalidator."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QMenu, QMessageBox, QRadioButton, QVBoxLayout

from ...core.events import ItemStatus
from ...core.naming import code_from_path
from ...core.operations import ValidateRequest, run_validation
from ...core.xtf import SourceFile, XtfInfo, expand_sources, read_header
from ..dialogs import IssuesDialog
from ..icons import icon
from ..widgets import (
    Banner, Card, Collapsible, DataTable, DropArea, PathEdit, button, hint, human_size, open_path,
    reveal_in_explorer, status_item,
)
from .base import OperationPage


class ValidatePage(OperationPage):
    key = "validate"
    title = "Validar XTF"
    subtitle = "Revise los archivos de transferencia contra el modelo INTERLIS antes de cargarlos."
    run_text = "Validar archivos"
    run_icon = "shield"

    COLS = ["Archivo", "Municipio", "Modelos (cabecera)", "Tamaño", "Estado", "Resultado"]

    def build_form(self) -> None:
        self.sources: list[SourceFile] = []
        self.headers: dict[str, XtfInfo] = {}
        self.outcome: dict[str, dict] = {}

        files = Card("Archivos a validar", "Agregue archivos .xtf, .zip o carpetas completas (se buscan en subcarpetas).", step=1)
        self.drop = DropArea("Arrastre aquí archivos XTF/ZIP o carpetas")
        self.drop.pathsAdded.connect(self.add_paths)
        files.body.addWidget(self.drop)
        self.table = DataTable(self.COLS, stretch_col=5)
        for col, w in ((0, 220), (1, 80), (2, 280), (3, 80), (4, 130)):
            self.table.setColumnWidth(col, w)
        self.table.setMinimumHeight(170)
        self.table.menu_builder = self._row_menu
        self.table.doubleClicked.connect(lambda idx: self._show_issues(idx.row()))
        files.body.addWidget(self.table)
        row = QHBoxLayout()
        self.count = hint("")
        row.addWidget(self.count, 1)
        rm = button("Quitar seleccionados", "x")
        rm.clicked.connect(self._remove_selected)
        clear = button("Limpiar lista", "trash")
        clear.clicked.connect(self._clear)
        row.addWidget(rm)
        row.addWidget(clear)
        files.body.addLayout(row)
        self.form.addWidget(files)

        opts = Card("Modelos", "ilivalidator toma los modelos declarados en la cabecera de cada XTF.", step=2)
        self.use_profile = QRadioButton()
        self.use_custom = QRadioButton("Usar otra carpeta de modelos:")
        self.custom_dir = PathEdit("dir", placeholder="Carpeta con archivos .ili")
        self.custom_dir.setEnabled(False)
        self.use_custom.toggled.connect(self.custom_dir.setEnabled)
        self.use_profile.setChecked(True)
        opts.body.addWidget(self.use_profile)
        line = QHBoxLayout()
        line.addWidget(self.use_custom)
        line.addWidget(self.custom_dir, 1)
        opts.body.addLayout(line)
        adv = Collapsible("Opciones avanzadas")
        self.chk_all_objects = QCheckBox("Verificar referencias entre todos los objetos (--allObjectsAccessible)")
        self.chk_all_objects.setToolTip("Asume que el archivo contiene todos los objetos referenciados: "
                                        "reporta referencias a objetos inexistentes.")
        self.chk_xtflog = QCheckBox("Generar además el reporte de errores en formato XTF (--xtflog)")
        adv.content_layout.addWidget(self.chk_all_objects)
        adv.content_layout.addWidget(self.chk_xtflog)
        opts.body.addWidget(adv)
        self.form.addWidget(opts)

        self.next_banner = Banner("success", "")
        self.next_banner.action.setText("Ir a Importar →")
        self.next_banner.action.show()
        self.next_banner.action.clicked.connect(self._go_import)
        self.next_banner.hide()
        self.form.addWidget(self.next_banner)

        self.ctx.profileChanged.connect(self._refresh_profile_label)
        self._refresh_profile_label()
        self._update_count()

    # ------------------------------------------------------------- lista
    def _refresh_profile_label(self) -> None:
        prof = self.ctx.model_profile()
        if prof:
            self.use_profile.setText(f"Usar la carpeta del perfil activo «{prof.name}»  ({prof.modeldir or 'sin carpeta'})")
        else:
            self.use_profile.setText("Usar el perfil de modelo activo (no hay ninguno configurado)")

    def receive(self, payload: dict) -> None:
        if payload.get("paths"):
            self.add_paths(payload["paths"])

    def add_paths(self, paths: list[str]) -> None:
        found, errors = expand_sources(paths)
        known = {str(s.path) for s in self.sources}
        for src in found:
            if str(src.path) in known:
                continue
            self.sources.append(src)
            self.headers[str(src.path)] = read_header(src.path)
        if errors:
            QMessageBox.warning(self, "Algunos archivos no se agregaron", "\n".join(errors))
        if not found and not errors:
            QMessageBox.information(self, "Sin archivos", "No se encontraron archivos .xtf en la selección.")
        self._fill()

    def _fill(self) -> None:
        self.table.setRowCount(len(self.sources))
        for r, src in enumerate(self.sources):
            h = self.headers.get(str(src.path))
            self.table.set_text(r, 0, src.display, tooltip=str(src.origin or src.path))
            self.table.set_text(r, 1, code_from_path(src.path, src.origin) or "-")
            models = "; ".join(h.model_names) if h and not h.error else (h.error if h else "")
            self.table.set_text(r, 2, models, tooltip=models)
            self.table.set_text(r, 3, human_size(h.size_bytes) if h else "")
            out = self.outcome.get(str(src.path))
            if out:
                self.table.setItem(r, 4, status_item(out["status"]))
                self.table.set_text(r, 5, out["detail"], tooltip=out["detail"])
            else:
                self.table.setItem(r, 4, status_item(ItemStatus.PENDING, "Sin validar"))
                self.table.set_text(r, 5, "")
        self._update_count()

    def _update_count(self) -> None:
        n = len(self.sources)
        size = sum(h.size_bytes for h in self.headers.values())
        self.count.setText(f"{n} archivo(s), {human_size(size)}" if n else "No hay archivos en la lista")

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            src = self.sources.pop(r)
            self.headers.pop(str(src.path), None)
            self.outcome.pop(str(src.path), None)
        self._fill()

    def _clear(self) -> None:
        self.sources.clear()
        self.headers.clear()
        self.outcome.clear()
        self.next_banner.hide()
        self._fill()

    def _row_menu(self, row: int, menu: QMenu) -> None:
        src = self.sources[row]
        out = self.outcome.get(str(src.path), {})
        if out.get("csv") and Path(out["csv"]).exists():
            menu.addAction(icon("list"), "Ver errores en tabla", lambda: self._show_issues(row))
        if out.get("log_file") and Path(out["log_file"]).exists():
            menu.addAction(icon("log"), "Abrir log de validación", lambda: open_path(out["log_file"]))
        menu.addAction(icon("folder"), "Mostrar en el explorador", lambda: reveal_in_explorer(src.origin or src.path))

    def _show_issues(self, row: int) -> None:
        if row < 0 or row >= len(self.sources):
            return
        src = self.sources[row]
        out = self.outcome.get(str(src.path), {})
        if not out.get("csv") or not Path(out["csv"]).exists():
            return
        IssuesDialog(src.display, out["csv"], out.get("log_file", ""), self).exec()

    # ----------------------------------------------------------- ejecución
    def _modeldir(self) -> str:
        if self.use_custom.isChecked():
            return self.custom_dir.text()
        prof = self.ctx.model_profile()
        return prof.modeldir if prof else ""

    def start(self) -> None:
        if not self.sources:
            QMessageBox.information(self, "Validar XTF", "Agregue al menos un archivo XTF.")
            return
        tools = self.ctx.tools()
        if not Path(tools.ilivalidator_jar).is_file():
            QMessageBox.critical(self, "ilivalidator no encontrado",
                                 f"No existe el archivo:\n{tools.ilivalidator_jar}\n\nRevise Configuración > Herramientas.")
            return
        req = ValidateRequest(tools, list(self.sources), modeldir=self._modeldir(),
                              xtflog=self.chk_xtflog.isChecked(), csvlog=True,
                              all_objects_accessible=self.chk_all_objects.isChecked())
        self.outcome.clear()
        self.next_banner.hide()
        self._fill()
        self.run_job(run_validation, req, items=[(str(s.path), s.display) for s in self.sources])

    def on_item(self, key: str, status: str, detail: str, data: dict) -> None:
        super().on_item(key, status, detail, data)
        rec = self.outcome.setdefault(key, {})
        rec.update(status=status, detail=detail, **data)
        for r, src in enumerate(self.sources):
            if str(src.path) == key:
                self.table.setItem(r, 4, status_item(status))
                self.table.set_text(r, 5, detail, tooltip=detail)
                break

    def on_results(self, results) -> None:
        for r in results:
            if r.key in self.outcome:
                self.outcome[r.key]["csv"] = r.extra.get("csv", "")
                self.outcome[r.key]["log_file"] = r.log_file
        valid = [r for r in results if r.status in (ItemStatus.OK, ItemStatus.WARNING)]
        if valid:
            self.next_banner.set("success", f"<b>{len(valid)} de {len(results)}</b> archivo(s) son válidos. "
                                            "Puede continuar con la importación de los archivos válidos.")
            self._valid_paths = [r.key for r in valid]
            self.next_banner.action.show()
        elif results:
            self.next_banner.set("error", "Ningún archivo supero la validación. Haga doble clic en un archivo "
                                          "para ver el detalle de los errores.")
            self.next_banner.action.hide()

    def _go_import(self) -> None:
        paths = [str(s.origin or s.path) for s in self.sources if str(s.path) in getattr(self, "_valid_paths", [])]
        self.ctx.navigateRequested.emit("import")
        window = self.window()
        if hasattr(window, "deliver"):
            window.deliver("import", {"paths": paths})
