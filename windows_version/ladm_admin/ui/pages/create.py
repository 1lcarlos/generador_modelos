"""Paso 2: crear esquemas (ili2pg --schemaimport)."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPlainTextEdit,
    QRadioButton,
)

from ...core.database import Database
from ...core.events import ItemStatus
from ...core.ili2db import Ili2pg, SCHEMA_OPTIONS
from ...core.naming import StorageMode, code_from_path, validate_identifier
from ...core.operations import CreateRequest, ExistingSchemaAction, check_create_request, run_create
from ...core.process import mask_command
from ...core.xtf import expand_sources
from ..widgets import Banner, Card, Collapsible, DataTable, button, hint, label, status_item
from .base import OperationPage


class CreatePage(OperationPage):
    key = "create"
    title = "Crear esquema"
    subtitle = "Genere la estructura de tablas LADM-COL en PostgreSQL a partir del perfil de modelo."
    run_text = "Crear esquemas"
    run_icon = "database"

    def build_form(self) -> None:
        # ---------------------------------------------------------- destino
        dest = Card("Destino", "Elija como organizar los municipios en la base de datos.", step=1)
        self.mode_group = QButtonGroup(self)
        self.rb_per = QRadioButton("Un esquema por municipio")
        self.rb_shared = QRadioButton("Un esquema único con un dataset por municipio")
        self.mode_group.addButton(self.rb_per)
        self.mode_group.addButton(self.rb_shared)
        self.rb_per.setChecked(True)
        modes = QHBoxLayout()
        modes.addWidget(self.rb_per)
        modes.addWidget(self.rb_shared)
        modes.addStretch(1)
        dest.body.addLayout(modes)

        self.per_hint = hint("")
        dest.body.addWidget(self.per_hint)
        self.codes = QPlainTextEdit()
        self.codes.setPlaceholderText("Codigos DIVIPOLA o nombres de esquema, uno por línea o separados por coma.\n"
                                      "Ej: 25279, 25436  ->  cun25279, cun25436")
        self.codes.setFixedHeight(80)
        dest.body.addWidget(self.codes)
        tools_row = QHBoxLayout()
        from_xtf = button("Tomar municipios de archivos XTF...", "file")
        from_xtf.clicked.connect(self._codes_from_xtf)
        check = button("Verificar en la base de datos", "search")
        check.clicked.connect(self._check_db)
        tools_row.addWidget(from_xtf)
        tools_row.addWidget(check)
        tools_row.addStretch(1)
        dest.body.addLayout(tools_row)

        self.shared_row = QFormLayout()
        self.shared_name = QLineEdit()
        self.shared_name.setPlaceholderText("ej. sinic_cundinamarca")
        self.shared_row.addRow("Nombre del esquema:", self.shared_name)
        dest.body.addLayout(self.shared_row)
        self.preview = DataTable(["Esquema", "Estado en la base de datos"], stretch_col=1)
        self.preview.setColumnWidth(0, 220)
        self.preview.setMaximumHeight(150)
        dest.body.addWidget(self.preview)
        self.form.addWidget(dest)

        # ----------------------------------------------------------- modelo
        model = Card("Modelo", "Se usa el perfil de modelo activo (selector superior).", step=2)
        self.model_info = label("", wrap=True)
        self.model_info.setTextFormat(Qt.RichText)
        model.body.addWidget(self.model_info)
        self.model_banner = Banner("warning", "")
        model.body.addWidget(self.model_banner)
        edit = button("Editar perfil de modelo", "settings", "link")
        edit.clicked.connect(lambda: self.ctx.navigateRequested.emit("settings"))
        model.header_tools.addWidget(edit)
        self.form.addWidget(model)

        # ------------------------------------------------------- existentes
        exist = Card("Si el esquema ya existe", step=3)
        self.on_existing = QComboBox()
        for action in (ExistingSchemaAction.ASK, ExistingSchemaAction.SKIP, ExistingSchemaAction.UPDATE,
                       ExistingSchemaAction.RECREATE):
            self.on_existing.addItem(action.label, action)
        exist.body.addWidget(self.on_existing)
        exist.body.addWidget(hint("Al recrear, el esquema original se respalda y solo se elimina si la nueva "
                                  "creación termina bien; si falla, se restaura automáticamente."))
        cmd = Collapsible("Vista previa del comando ili2pg")
        self.cmd_preview = QPlainTextEdit()
        self.cmd_preview.setReadOnly(True)
        self.cmd_preview.setObjectName("Log")
        self.cmd_preview.setFixedHeight(90)
        cmd.content_layout.addWidget(self.cmd_preview)
        copy = button("Copiar comando", "copy")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.cmd_preview.toPlainText()))
        cmd.content_layout.addWidget(copy, 0, Qt.AlignLeft)
        cmd.toggle.toggled.connect(lambda on: on and self._update_preview())
        exist.body.addWidget(cmd)
        self.form.addWidget(exist)

        self.rb_per.toggled.connect(self._mode_changed)
        self.codes.textChanged.connect(self._schemas_changed)
        self.shared_name.textChanged.connect(self._schemas_changed)
        self.ctx.profileChanged.connect(self._refresh_model)
        self.ctx.settingsChanged.connect(self._refresh_model)
        self.ctx.connectionChanged.connect(lambda: self.preview.setRowCount(0))
        self._mode_changed()
        self._refresh_model()

    # ------------------------------------------------------------ helpers
    def on_shown(self) -> None:
        self._refresh_model()

    def receive(self, payload: dict) -> None:
        if payload.get("codes"):
            self.rb_per.setChecked(True)
            self.codes.setPlainText(", ".join(payload["codes"]))

    def storage_mode(self) -> StorageMode:
        return StorageMode.SHARED if self.rb_shared.isChecked() else StorageMode.PER_MUNICIPALITY

    def _mode_changed(self) -> None:
        per = self.rb_per.isChecked()
        self.codes.setVisible(per)
        self.per_hint.setVisible(per)
        for i in range(self.shared_row.rowCount()):
            for role in (QFormLayout.LabelRole, QFormLayout.FieldRole):
                item = self.shared_row.itemAt(i, role)
                if item and item.widget():
                    item.widget().setVisible(not per)
        prefix = self.ctx.settings.schema_prefix
        self.per_hint.setText(f"Cada código de municipio genera el esquema <b>{prefix}&lt;código&gt;</b> "
                              f"(el prefijo se cambia en Configuración).")
        self._schemas_changed()
        self._refresh_model()

    def schemas(self) -> list[str]:
        if self.rb_shared.isChecked():
            name = self.shared_name.text().strip().lower()
            return [name] if name else []
        naming = self.ctx.naming()
        result = []
        for token in re.split(r"[,\s;]+", self.codes.toPlainText()):
            token = token.strip().lower()
            if not token:
                continue
            name = naming.schema_for_code(token) if token.isdigit() else token
            if name not in result:
                result.append(name)
        return result

    def _schemas_changed(self) -> None:
        names = self.schemas()
        self.preview.setRowCount(len(names))
        for r, name in enumerate(names):
            self.preview.set_text(r, 0, name)
            err = validate_identifier(name)
            if err:
                self.preview.setItem(r, 1, status_item(ItemStatus.ERROR, err))
            else:
                self.preview.setItem(r, 1, status_item(ItemStatus.PENDING, "Sin verificar"))

    def _codes_from_xtf(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Archivos XTF o ZIP", "", "Transferencias (*.xtf *.zip)")
        if not files:
            return
        found, _ = expand_sources(files)
        codes = sorted({c for c in (code_from_path(s.path, s.origin) for s in found) if c})
        if not codes:
            QMessageBox.information(self, "Sin códigos", "No se detectó un código de municipio en los nombres.")
            return
        current = self.codes.toPlainText().strip()
        self.codes.setPlainText((current + ", " if current else "") + ", ".join(codes))

    def _check_db(self) -> None:
        params = self.ctx.connection_params(self)
        names = self.schemas()
        if params is None or not names:
            return

        def work():
            db = Database(params)
            if not db.database_exists():
                return None
            return {n: db.inspect_schema(n) for n in names}

        def done(infos):
            for r, name in enumerate(names):
                if infos is None:
                    self.preview.setItem(r, 1, status_item(ItemStatus.PENDING,
                                                           f"La base de datos '{params.database}' no existe: se creará"))
                    continue
                info = infos[name]
                if not info.exists:
                    self.preview.setItem(r, 1, status_item(ItemStatus.OK, "No existe: se creará"))
                elif not info.is_ili2db:
                    self.preview.setItem(r, 1, status_item(ItemStatus.ERROR, "Existe pero no es un esquema ili2db"))
                else:
                    ver = info.ili2db_version or "?"
                    data = f"datasets: {', '.join(info.datasets)}" if info.datasets else "sin datos"
                    self.preview.setItem(r, 1, status_item(ItemStatus.WARNING,
                                                           f"Ya existe (ili2pg {ver}, {info.table_count} tablas, {data})"))

        self.run_helper(work, done)

    def _refresh_model(self) -> None:
        prof = self.ctx.model_profile()
        if prof is None:
            self.model_info.setText("No hay un perfil de modelo activo. Cree uno en <b>Configuración</b>.")
            self.model_banner.set("warning", "")
            return
        opts = prof.normalized_options()
        enabled = [o.label for o in SCHEMA_OPTIONS if opts.get(o.flag)]
        self.model_info.setText(
            f"<b>{prof.name}</b><br>"
            f"Modelos: {', '.join(prof.models) or '<i>ninguno</i>'}<br>"
            f"Carpeta: {prof.modeldir or '<i>no definida</i>'}<br>"
            f"EPSG: {prof.srs_code} &nbsp;·&nbsp; Script previo: {prof.prescript or 'ninguno'}<br>"
            f"<span style='color:gray'>{len(enabled)} opciones de ili2pg activas</span>")
        warn = []
        if not opts.get("createBasketCol"):
            warn.append("El perfil no tiene activa la <b>columna de basket</b>: los modelos LADM-COL (SINIC, "
                        "Interno ACC) la requieren y sin ella no se podrá reemplazar datos al importar.")
        if not prof.models:
            warn.append("El perfil no tiene modelos seleccionados.")
        self.model_banner.set("warning", "<br>".join(warn))
        self._update_preview()

    def _request(self, params) -> CreateRequest | None:
        prof = self.ctx.model_profile()
        if prof is None:
            return None
        return CreateRequest(params, self.ctx.tools(), prof, self.schemas(), self.ctx.settings.effective_log_dir(),
                             on_existing=self.on_existing.currentData(), storage_mode=self.storage_mode())

    def _update_preview(self) -> None:
        prof = self.ctx.model_profile()
        conn = self.ctx.connection_profile()
        names = self.schemas()
        if not prof or not conn or not names:
            self.cmd_preview.setPlainText("Complete el destino, la conexión y el perfil de modelo.")
            return
        cmd = Ili2pg(self.ctx.tools(), conn.params("****"), modeldir=prof.modeldir).schema_import(
            names[0], prof.models, prof.srs_code, prof.normalized_options(), prescript=prof.prescript)
        extra = f"\n\n# ... y {len(names) - 1} esquema(s) más" if len(names) > 1 else ""
        self.cmd_preview.setPlainText(mask_command(cmd) + extra)

    # ----------------------------------------------------------- ejecución
    def start(self) -> None:
        if self.ctx.connection_profile() is None:
            QMessageBox.information(self, "Sin conexión", "Configure una conexión a la base de datos primero.")
            return
        params = self.ctx.connection_params(self)
        if params is None:
            return
        req = self._request(params)
        if req is None:
            QMessageBox.information(self, "Sin perfil", "Seleccione un perfil de modelo.")
            return
        problems = check_create_request(req)
        if problems:
            QMessageBox.warning(self, "Revise la configuración", "\n".join(f"• {p}" for p in problems))
            return
        msg = (f"Se crearán {len(req.schemas)} esquema(s) en <b>{params.describe()}</b> "
               f"con el perfil <b>{req.profile.name}</b>.<br><br>" + "<br>".join(req.schemas[:12])
               + ("<br>..." if len(req.schemas) > 12 else ""))
        if QMessageBox.question(self, "Confirmar creación", msg) != QMessageBox.Yes:
            return
        decide = lambda info: self.bridge.ask("existing_schema", info, default=(ExistingSchemaAction.ABORT, False))
        self.run_job(run_create, req, items=[(s, s) for s in req.schemas], decide=decide)

    def on_results(self, results) -> None:
        if any(r.status == ItemStatus.OK for r in results):
            self._check_db()
