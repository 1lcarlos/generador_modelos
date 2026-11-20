"""Paso 3: importar XTF a esquemas existentes."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QMenu, QMessageBox, QRadioButton, QTableWidgetItem,
)

from ...core.database import Database
from ...core.events import ItemStatus
from ...core.ili2db import ImportMode
from ...core.naming import StorageMode
from ...core.operations import (
    ImportItem, ImportRequest, PlanState, analyze_import, reevaluate_import, run_import,
)
from ...core.events import Reporter
from ...core.xtf import SourceFile, expand_sources
from ..icons import icon
from ..widgets import (
    Banner, Card, Collapsible, DataTable, DropArea, button, hint, reveal_in_explorer, status_item,
)
from .base import OperationPage

_STATE_STATUS = {PlanState.READY: ItemStatus.OK, PlanState.CONFLICT: ItemStatus.WARNING,
                 PlanState.BLOCKED: ItemStatus.ERROR}


class ImportPage(OperationPage):
    key = "import"
    title = "Importar XTF"
    subtitle = "Cargue los datos de los archivos XTF en esquemas ya creados."
    run_text = "Importar"
    run_icon = "import"

    COLS = ["", "Archivo", "Municipio", "Esquema destino", "Dataset", "Objetos", "Estado", "Observaciones"]
    C_CHECK, C_FILE, C_CODE, C_SCHEMA, C_DATASET, C_OBJ, C_STATE, C_NOTES = range(8)

    def build_form(self) -> None:
        self.sources: list[SourceFile] = []
        self.items: list[ImportItem] = []
        self._filling = False
        self._analysis_job = None

        # ---------------------------------------------------------- destino
        dest = Card("Destino", "Defina como se ubica cada municipio en la base de datos.", step=1)
        self.mode_group = QButtonGroup(self)
        self.rb_per = QRadioButton("Un esquema por municipio")
        self.rb_shared = QRadioButton("Esquema único:")
        self.mode_group.addButton(self.rb_per)
        self.mode_group.addButton(self.rb_shared)
        self.rb_per.setChecked(True)
        self.shared_schema = QComboBox()
        self.shared_schema.setEditable(True)
        self.shared_schema.setMinimumWidth(240)
        self.shared_schema.setEnabled(False)
        self.shared_schema.lineEdit().setPlaceholderText("Seleccione o escriba el esquema")
        load = button("", "refresh", tooltip="Cargar esquemas ili2db de la base de datos")
        load.clicked.connect(self._load_schemas)
        row = QHBoxLayout()
        row.addWidget(self.rb_per)
        row.addSpacing(20)
        row.addWidget(self.rb_shared)
        row.addWidget(self.shared_schema)
        row.addWidget(load)
        row.addStretch(1)
        dest.body.addLayout(row)
        self.mode_hint = hint("")
        dest.body.addWidget(self.mode_hint)
        self.form.addWidget(dest)

        # --------------------------------------------------------- archivos
        files = Card("Archivos y plan de importación",
                     "Se leen las cabeceras y se revisa cada destino en la base de datos antes de importar. "
                     "Puede corregir el esquema o el dataset con doble clic.", step=2)
        self.btn_analyze = button("Analizar", "search")
        self.btn_analyze.clicked.connect(self.analyze)
        files.header_tools.addWidget(self.btn_analyze)
        self.drop = DropArea("Arrastre aquí archivos XTF/ZIP o carpetas (se recomienda validarlos primero)")
        self.drop.pathsAdded.connect(self.add_paths)
        files.body.addWidget(self.drop)
        self.table = DataTable(self.COLS, stretch_col=self.C_NOTES)
        for col, w in ((self.C_CHECK, 30), (self.C_FILE, 190), (self.C_CODE, 75), (self.C_SCHEMA, 150),
                       (self.C_DATASET, 100), (self.C_OBJ, 75), (self.C_STATE, 130)):
            self.table.setColumnWidth(col, w)
        self.table.setMinimumHeight(190)
        self.table.setEditTriggers(DataTable.DoubleClicked | DataTable.EditKeyPressed)
        self.table.itemChanged.connect(self._cell_edited)
        self.table.menu_builder = self._row_menu
        files.body.addWidget(self.table)
        bottom = QHBoxLayout()
        self.summary = hint("")
        bottom.addWidget(self.summary, 1)
        rm = button("Quitar seleccionados", "x")
        rm.clicked.connect(self._remove_selected)
        clear = button("Limpiar", "trash")
        clear.clicked.connect(self._clear)
        bottom.addWidget(rm)
        bottom.addWidget(clear)
        files.body.addLayout(bottom)
        self.plan_banner = Banner("info", "")
        files.body.addWidget(self.plan_banner)
        self.form.addWidget(files)

        # -------------------------------------------------------- conflicto
        conflict = Card("Si el destino ya tiene datos", step=3)
        self.conflict_group = QButtonGroup(self)
        options = [
            (ImportMode.ASK, "Preguntar en cada caso"),
            (ImportMode.REPLACE, "Reemplazar los datos existentes del municipio"),
            (ImportMode.APPEND, "Agregar como un nuevo dataset"),
            (ImportMode.CANCEL, "No importar ese archivo"),
        ]
        crow = QHBoxLayout()
        for mode, text in options:
            rb = QRadioButton(text)
            rb.setProperty("mode", mode.value)
            self.conflict_group.addButton(rb)
            crow.addWidget(rb)
            rb.setChecked(mode == ImportMode.ASK)
        crow.addStretch(1)
        conflict.body.addLayout(crow)
        conflict.body.addWidget(hint("Reemplazar elimina y vuelve a cargar los datos del municipio en una sola "
                                     "transacción: si la importación falla, los datos anteriores se conservan."))

        adv = Collapsible("Opciones avanzadas")
        self.chk_validate = QCheckBox("Validar los datos durante la importación (recomendado)")
        self.chk_validate.setChecked(True)
        self.chk_verify = QCheckBox("Verificar después de importar que los conteos por clase coincidan con el XTF")
        self.chk_verify.setChecked(True)
        self.chk_skip_ref = QCheckBox("Omitir errores de referencia (requiere esquema creado con 'Permitir NULL')")
        self.chk_skip_geom = QCheckBox("Omitir errores de geometría")
        for w in (self.chk_validate, self.chk_verify, self.chk_skip_ref, self.chk_skip_geom):
            adv.content_layout.addWidget(w)
        conflict.body.addWidget(adv)
        self.form.addWidget(conflict)

        self._reanalyze_timer = QTimer(self)
        self._reanalyze_timer.setSingleShot(True)
        self._reanalyze_timer.setInterval(400)
        self._reanalyze_timer.timeout.connect(self._reevaluate)

        self.rb_per.toggled.connect(self._mode_changed)
        self.shared_schema.currentTextChanged.connect(lambda _: self._mode_changed())
        self.ctx.connectionChanged.connect(self._invalidate)
        self._mode_changed()
        self._fill()

    # ------------------------------------------------------------ estado
    def receive(self, payload: dict) -> None:
        if payload.get("paths"):
            self.add_paths(payload["paths"])

    def storage_mode(self) -> StorageMode:
        return StorageMode.SHARED if self.rb_shared.isChecked() else StorageMode.PER_MUNICIPALITY

    def conflict_mode(self) -> ImportMode:
        btn = self.conflict_group.checkedButton()
        return ImportMode(btn.property("mode")) if btn else ImportMode.ASK

    def _mode_changed(self) -> None:
        shared = self.rb_shared.isChecked()
        self.shared_schema.setEnabled(shared)
        prefix = self.ctx.settings.schema_prefix
        if shared:
            self.mode_hint.setText("Todos los archivos se importan al esquema elegido; cada municipio queda en "
                                   "su propio <b>dataset</b> (código DIVIPOLA).")
        else:
            self.mode_hint.setText(f"Cada archivo se importa al esquema <b>{prefix}&lt;código&gt;</b>, detectado "
                                   "del nombre del archivo o de su carpeta.")
        if self.items:
            for item in self.items:
                item.schema = ""
            self._invalidate()
            self._schedule_reanalysis(full=True)

    def _invalidate(self) -> None:
        for item in self.items:
            item.schema_info = None

    def _load_schemas(self) -> None:
        params = self.ctx.connection_params(self)
        if params is None:
            return

        def done(names):
            current = self.shared_schema.currentText()
            self.shared_schema.clear()
            self.shared_schema.addItems(names)
            self.shared_schema.setEditText(current)
            self.rb_shared.setChecked(True)

        self.run_helper(lambda: Database(params).list_schemas(only_ili2db=True), done)

    # ------------------------------------------------------------ fuentes
    def add_paths(self, paths: list[str]) -> None:
        found, errors = expand_sources(paths)
        known = {str(s.path) for s in self.sources}
        new = [s for s in found if str(s.path) not in known]
        self.sources.extend(new)
        if errors:
            QMessageBox.warning(self, "Algunos archivos no se agregaron", "\n".join(errors))
        if new:
            self.analyze()
        elif not errors:
            QMessageBox.information(self, "Sin archivos nuevos", "No se encontraron archivos .xtf nuevos.")

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        keys = {self.items[r].key for r in rows if r < len(self.items)}
        self.items = [it for it in self.items if it.key not in keys]
        self.sources = [s for s in self.sources if str(s.path) not in keys]
        self._schedule_reanalysis()

    def _clear(self) -> None:
        self.items.clear()
        self.sources.clear()
        self._fill()

    # ------------------------------------------------------------ análisis
    def _request(self, params) -> ImportRequest | None:
        prof = self.ctx.model_profile()
        return ImportRequest(
            params, self.ctx.tools(), prof.modeldir if prof else "", self.ctx.settings.effective_log_dir(),
            storage_mode=self.storage_mode(), naming=self.ctx.naming(),
            shared_schema=self.shared_schema.currentText().strip(),
            conflict_mode=self.conflict_mode(),
            disable_validation=not self.chk_validate.isChecked(),
            skip_reference_errors=self.chk_skip_ref.isChecked(),
            skip_geometry_errors=self.chk_skip_geom.isChecked(),
            verify_counts=self.chk_verify.isChecked(),
        )

    def analyze(self) -> None:
        if not self.sources:
            self._fill()
            return
        params = self.ctx.connection_params(self)
        if params is None:
            return
        req = self._request(params)
        existing = {it.key: it for it in self.items}
        pending = [s for s in self.sources if str(s.path) not in existing]
        self.btn_analyze.setEnabled(False)
        self.plan_banner.set("info", f"Analizando {len(self.sources)} archivo(s)...")

        def work():
            new_items = analyze_import(req, pending, Reporter(), scan_objects=True) if pending else []
            merged = {it.key: it for it in new_items}
            merged.update(existing)
            ordered = [merged[str(s.path)] for s in self.sources if str(s.path) in merged]
            for it in ordered:
                if req.storage_mode == StorageMode.SHARED:
                    it.schema = req.shared_schema
                elif not it.schema and it.code:
                    it.schema = req.naming.schema_for_code(it.code)
            reevaluate_import(req, ordered, Reporter())
            return ordered

        def done(items):
            self.items = items
            self.btn_analyze.setEnabled(True)
            self._fill()

        def failed(tb):
            self.btn_analyze.setEnabled(True)
            self.plan_banner.set("error", "No se pudo analizar: " + tb.strip().splitlines()[-1])

        self.run_helper(work, done, on_error=failed)

    def _schedule_reanalysis(self, full: bool = False) -> None:
        self._fill()
        self._reanalyze_timer.start()

    def _reevaluate(self) -> None:
        if self.items or self.sources:
            self.analyze()

    # ---------------------------------------------------------------- tabla
    def _fill(self) -> None:
        self._filling = True
        self.table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if it.enabled else Qt.Unchecked)
            self.table.setItem(r, self.C_CHECK, chk)
            self.table.set_text(r, self.C_FILE, it.source.display, tooltip=str(it.source.origin or it.source.path))
            self.table.set_text(r, self.C_CODE, it.code or "-")
            sch = QTableWidgetItem(it.schema)
            sch.setFlags(sch.flags() | Qt.ItemIsEditable if self.rb_per.isChecked() else sch.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, self.C_SCHEMA, sch)
            ds = QTableWidgetItem(it.dataset or "")
            ds.setFlags(ds.flags() | Qt.ItemIsEditable)
            self.table.setItem(r, self.C_DATASET, ds)
            total = it.header.total_objects
            self.table.set_text(r, self.C_OBJ, f"{total:,}".replace(",", ".") if total else "-")
            if not it.enabled:
                self.table.setItem(r, self.C_STATE, status_item(ItemStatus.SKIPPED, "Excluido"))
            else:
                self.table.setItem(r, self.C_STATE, status_item(_STATE_STATUS[it.state], it.state.label))
            notes = "; ".join(it.messages + it.warnings)
            if it.state == PlanState.CONFLICT and not notes:
                existing = ", ".join(it.schema_info.datasets) if it.schema_info and it.schema_info.datasets else ""
                notes = f"Datos existentes{': ' + existing if existing else ''}. Se aplicará: {self.conflict_mode().label.lower()}"
            self.table.set_text(r, self.C_NOTES, notes, tooltip=notes)
        for col in (self.C_FILE, self.C_CODE, self.C_OBJ, self.C_STATE, self.C_NOTES):
            for r in range(self.table.rowCount()):
                item = self.table.item(r, col)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self._filling = False
        self._update_summary()

    def _update_summary(self) -> None:
        active = [it for it in self.items if it.enabled]
        ready = sum(1 for it in active if it.state == PlanState.READY)
        conflict = sum(1 for it in active if it.state == PlanState.CONFLICT)
        blocked = sum(1 for it in active if it.state == PlanState.BLOCKED)
        objs = sum(it.header.total_objects for it in active)
        if not self.items:
            self.summary.setText("Agregue archivos para ver el plan de importación.")
            self.plan_banner.set("info", "")
            return
        self.summary.setText(f"{len(active)} de {len(self.items)} archivo(s) seleccionados · "
                             f"{objs:,} objetos".replace(",", "."))
        msgs = []
        if ready:
            msgs.append(f"<b>{ready}</b> listo(s) para importar")
        if conflict:
            msgs.append(f"<b>{conflict}</b> con datos existentes")
        if blocked:
            msgs.append(f"<b>{blocked}</b> bloqueado(s) (ver observaciones)")
        kind = "error" if blocked and not (ready or conflict) else ("warning" if blocked or conflict else "success")
        text = " · ".join(msgs)
        if blocked and any("no existe" in m for it in active for m in it.messages):
            text += "<br>Hay esquemas que no existen: créelos en el paso <b>Crear esquema</b>."
        self.plan_banner.set(kind, text)

    def _cell_edited(self, cell: QTableWidgetItem) -> None:
        if self._filling:
            return
        r, c = cell.row(), cell.column()
        if r >= len(self.items):
            return
        it = self.items[r]
        if c == self.C_CHECK:
            it.enabled = cell.checkState() == Qt.Checked
        elif c == self.C_SCHEMA:
            it.schema = cell.text().strip().lower()
            it.schema_info = None
        elif c == self.C_DATASET:
            it.dataset = cell.text().strip() or None
        else:
            return
        self._schedule_reanalysis()

    def _row_menu(self, row: int, menu: QMenu) -> None:
        if row >= len(self.items):
            return
        it = self.items[row]
        menu.addAction(icon("folder"), "Mostrar en el explorador",
                       lambda: reveal_in_explorer(it.source.origin or it.source.path))
        if it.header.class_counts:
            def show_counts():
                lines = "\n".join(f"{n:>8}  {c}" for c, n in it.header.class_counts.most_common())
                QMessageBox.information(self, f"Contenido de {it.source.display}",
                                        f"Modelos: {', '.join(it.header.model_names)}\n\n{lines}")
            menu.addAction(icon("list"), "Ver objetos por clase", show_counts)

    # ----------------------------------------------------------- ejecución
    def start(self) -> None:
        if not self.items:
            QMessageBox.information(self, "Importar", "Agregue archivos y analice el plan primero.")
            return
        if self.rb_shared.isChecked() and not self.shared_schema.currentText().strip():
            QMessageBox.information(self, "Importar", "Indique el esquema único de destino.")
            return
        params = self.ctx.connection_params(self)
        if params is None:
            return
        active = [it for it in self.items if it.enabled]
        runnable = [it for it in active if it.state != PlanState.BLOCKED]
        if not runnable:
            QMessageBox.warning(self, "Nada para importar",
                                "Todos los archivos seleccionados están bloqueados. Revise la columna Observaciones.")
            return
        blocked = len(active) - len(runnable)
        req = self._request(params)
        text = (f"Se importarán <b>{len(runnable)}</b> archivo(s) en <b>{params.describe()}</b>."
                + (f"<br>{blocked} archivo(s) bloqueado(s) no se importarán (quedarán registrados como error con su motivo)." if blocked else "")
                + f"<br><br>Si el destino ya tiene datos: <b>{req.conflict_mode.label}</b>")
        if not req.disable_validation:
            text += "<br>Los datos se validan durante la importación."
        if QMessageBox.question(self, "Confirmar importación", text) != QMessageBox.Yes:
            return
        decide = lambda item: self.bridge.ask("import_conflict", item, default=(None, False))
        # Los bloqueados también se envían: quedan en Resultados como error con su motivo (trazabilidad)
        self.run_job(run_import, req, active, items=[(it.key, it.source.display) for it in active], decide=decide)

    def on_results(self, results) -> None:
        self._schedule_reanalysis()
