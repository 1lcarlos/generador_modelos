"""Paso 4: exportar esquemas o datasets a XTF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QRadioButton,
    QTableWidgetItem,
)

from ...core.database import Database
from ...core.events import ItemStatus
from ...core.naming import StorageMode
from ...core.operations import ExportRequest, ExportTarget, run_export
from ..widgets import Banner, Card, Collapsible, DataTable, PathEdit, button, hint
from .base import OperationPage


class ExportPage(OperationPage):
    key = "export"
    title = "Exportar XTF"
    subtitle = "Genere archivos de transferencia XTF desde los esquemas de la base de datos."
    run_text = "Exportar"
    run_icon = "export"

    COLS = ["", "Esquema", "Municipio / dataset", "Datasets", "Modelos", "ili2pg"]

    def build_form(self) -> None:
        self.targets: list[tuple[ExportTarget, dict]] = []

        src = Card("Origen", "Cargue los esquemas desde la base de datos y marque los que desea exportar.", step=1)
        self.mode_group = QButtonGroup(self)
        self.rb_per = QRadioButton("Esquemas por municipio")
        self.rb_shared = QRadioButton("Datasets de un esquema único:")
        self.mode_group.addButton(self.rb_per)
        self.mode_group.addButton(self.rb_shared)
        self.rb_per.setChecked(True)
        self.shared_schema = QComboBox()
        self.shared_schema.setEditable(True)
        self.shared_schema.setMinimumWidth(220)
        self.shared_schema.setEnabled(False)
        self.rb_shared.toggled.connect(self.shared_schema.setEnabled)
        row = QHBoxLayout()
        row.addWidget(self.rb_per)
        row.addSpacing(20)
        row.addWidget(self.rb_shared)
        row.addWidget(self.shared_schema)
        row.addStretch(1)
        src.body.addLayout(row)

        tools = QHBoxLayout()
        self.btn_load = button("Cargar desde la base de datos", "refresh")
        self.btn_load.clicked.connect(self.load_targets)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrar...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        self.only_prefix = QCheckBox()
        self.only_prefix.setChecked(True)
        self.only_prefix.toggled.connect(self._fill)
        all_btn = button("Todos", tooltip="Marcar todos los visibles")
        none_btn = button("Ninguno")
        all_btn.clicked.connect(lambda: self._check_all(True))
        none_btn.clicked.connect(lambda: self._check_all(False))
        tools.addWidget(self.btn_load)
        tools.addWidget(self.filter, 1)
        tools.addWidget(self.only_prefix)
        tools.addWidget(all_btn)
        tools.addWidget(none_btn)
        src.body.addLayout(tools)
        self.table = DataTable(self.COLS, stretch_col=4)
        for col, w in ((0, 30), (1, 170), (2, 140), (3, 160), (5, 70)):
            self.table.setColumnWidth(col, w)
        self.table.setMinimumHeight(200)
        self.table.itemChanged.connect(lambda _: self._update_count())
        src.body.addWidget(self.table)
        self.count = hint("")
        src.body.addWidget(self.count)
        self.form.addWidget(src)

        out = Card("Salida", step=2)
        form = QFormLayout()
        self.output = PathEdit("dir", placeholder="Carpeta donde se crearán las subcarpetas por municipio")
        self.output.setText(self.ctx.settings.ui.get("export_dir", ""))
        form.addRow("Carpeta de salida:", self.output)
        out.body.addLayout(form)
        out.body.addWidget(hint("Por cada municipio se crea <b>&lt;salida&gt;/&lt;código&gt;/&lt;código&gt;.xtf</b> "
                                "y su log de exportación. Los archivos existentes se sobrescriben."))
        adv = Collapsible("Opciones avanzadas")
        self.chk_tid = QCheckBox("Exportar los TID originales (t_ili_tid) — recomendado")
        self.chk_tid.setChecked(True)
        self.chk_validate = QCheckBox("Validar los datos durante la exportación")
        self.chk_validate.setChecked(True)
        adv.content_layout.addWidget(self.chk_tid)
        adv.content_layout.addWidget(self.chk_validate)
        out.body.addWidget(adv)
        self.form.addWidget(out)

        self.done_banner = Banner("success", "")
        self.done_banner.action.setText("Validar archivos exportados →")
        self.done_banner.action.show()
        self.done_banner.action.clicked.connect(self._go_validate)
        self.done_banner.hide()
        self.form.addWidget(self.done_banner)

        self.ctx.connectionChanged.connect(lambda: (self.table.setRowCount(0), self.targets.clear(), self._update_count()))
        self.ctx.settingsChanged.connect(self._refresh_prefix)
        self._refresh_prefix()
        self._update_count()

    def _refresh_prefix(self) -> None:
        self.only_prefix.setText(f"Solo '{self.ctx.settings.schema_prefix}*'")

    # ---------------------------------------------------------------- carga
    def load_targets(self) -> None:
        params = self.ctx.connection_params(self)
        if params is None:
            return
        shared = self.rb_shared.isChecked()
        schema = self.shared_schema.currentText().strip()
        naming = self.ctx.naming()
        self.btn_load.setEnabled(False)

        def work():
            db = Database(params)
            names = db.list_schemas(only_ili2db=True)
            rows = []
            if shared:
                if not schema:
                    return names, []
                info = db.inspect_schema(schema)
                for ds in info.datasets:
                    rows.append((ExportTarget(schema, ds, ds), {"datasets": ds, "models": info.models,
                                                                 "version": info.ili2db_version}))
            else:
                for name in names:
                    info = db.inspect_schema(name)
                    rows.append((ExportTarget(name, naming.code_for_schema(name)),
                                 {"datasets": ", ".join(info.datasets) or ("con datos" if info.has_data else "sin datos"),
                                  "models": info.models, "version": info.ili2db_version}))
            return names, rows

        def done(result):
            names, rows = result
            self.btn_load.setEnabled(True)
            current = self.shared_schema.currentText()
            self.shared_schema.clear()
            self.shared_schema.addItems(names)
            self.shared_schema.setEditText(current)
            self.targets = rows
            self._fill()
            if shared and not schema:
                QMessageBox.information(self, "Esquema único", "Seleccione el esquema y vuelva a cargar.")

        def failed(tb):
            self.btn_load.setEnabled(True)
            QMessageBox.critical(self, "Error", tb.strip().splitlines()[-1])

        self.run_helper(work, done, on_error=failed)

    def _fill(self) -> None:
        prefix = self.ctx.settings.schema_prefix.lower()
        rows = [(t, d) for t, d in self.targets
                if self.rb_shared.isChecked() or not self.only_prefix.isChecked() or t.schema.lower().startswith(prefix)]
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for r, (tgt, data) in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            chk.setData(Qt.UserRole, tgt)
            self.table.setItem(r, 0, chk)
            self.table.set_text(r, 1, tgt.schema)
            self.table.set_text(r, 2, tgt.code)
            self.table.set_text(r, 3, data["datasets"])
            models = ", ".join(data["models"])
            self.table.set_text(r, 4, models, tooltip=models)
            self.table.set_text(r, 5, data["version"] or "?")
        self.table.blockSignals(False)
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.filter.text().lower().strip()
        for r in range(self.table.rowCount()):
            hay = " ".join(self.table.item(r, c).text().lower() for c in (1, 2, 3) if self.table.item(r, c))
            self.table.setRowHidden(r, bool(text) and text not in hay)
        self._update_count()

    def _check_all(self, value: bool) -> None:
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                self.table.item(r, 0).setCheckState(Qt.Checked if value else Qt.Unchecked)
        self.table.blockSignals(False)
        self._update_count()

    def selected(self) -> list[ExportTarget]:
        return [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount())
                if self.table.item(r, 0).checkState() == Qt.Checked]

    def _update_count(self) -> None:
        total = self.table.rowCount()
        self.count.setText(f"{len(self.selected())} seleccionado(s) de {total}" if total
                           else "Pulse «Cargar desde la base de datos» para ver los esquemas disponibles.")

    # ------------------------------------------------------------ ejecución
    def start(self) -> None:
        targets = self.selected()
        if not targets:
            QMessageBox.information(self, "Exportar", "Marque al menos un esquema o dataset.")
            return
        out = self.output.text()
        if not out:
            QMessageBox.information(self, "Exportar", "Seleccione la carpeta de salida.")
            return
        params = self.ctx.connection_params(self)
        if params is None:
            return
        self.ctx.settings.ui["export_dir"] = out
        self.ctx.save()
        existing = [t for t in targets if (Path(out) / t.code / f"{t.code}.xtf").exists()]
        text = f"Se exportarán <b>{len(targets)}</b> destino(s) a <b>{out}</b>."
        if existing:
            text += f"<br><br>{len(existing)} archivo(s) ya existen y se sobrescribirán."
        if QMessageBox.question(self, "Confirmar exportación", text) != QMessageBox.Yes:
            return
        prof = self.ctx.model_profile()
        req = ExportRequest(params, self.ctx.tools(), prof.modeldir if prof else "", Path(out), targets,
                            export_tid=self.chk_tid.isChecked(), disable_validation=not self.chk_validate.isChecked())
        self.done_banner.hide()
        self.run_job(run_export, req, items=[(t.key, t.key) for t in targets])

    def on_results(self, results) -> None:
        self._exported = [r.output_file for r in results if r.output_file and r.status in (ItemStatus.OK, ItemStatus.WARNING)]
        if self._exported:
            self.done_banner.set("success", f"Se generaron <b>{len(self._exported)}</b> archivo(s) XTF en "
                                            f"<a href='file:///{self.output.text()}'>{self.output.text()}</a>.")

    def _go_validate(self) -> None:
        self.ctx.navigateRequested.emit("validate")
        window = self.window()
        if hasattr(window, "deliver"):
            window.deliver("validate", {"paths": getattr(self, "_exported", [])})
