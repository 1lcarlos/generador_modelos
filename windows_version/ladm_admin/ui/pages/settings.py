"""Configuración: conexiones, perfiles de modelo, herramientas y preferencias."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QScrollArea, QSpinBox, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ...core import paths
from ...core.database import Database
from ...core.ili import duplicate_models, scan_model_dir, suggested_models
from ...core.ili2db import SCHEMA_OPTIONS, default_schema_options
from ...core.process import java_version
from ...core.settings import (
    ConnectionProfile, ModelProfile, delete_password, get_password, import_legacy_profiles, keyring_available,
    legacy_profiles_available, set_password,
)
from ...core.naming import validate_identifier
from ..widgets import Banner, Card, PathEdit, button, hint, label
from ..worker import Job
from .base import Page


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setWidget(widget)
    return area


# ================================================================ conexiones
class ConnectionsTab(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._jobs: list[Job] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._load)
        ll.addWidget(self.list, 1)
        row = QHBoxLayout()
        new = button("Nueva", "plus")
        new.clicked.connect(self._new)
        self.delete = button("Eliminar", "trash", "danger")
        self.delete.clicked.connect(self._delete)
        row.addWidget(new)
        row.addWidget(self.delete)
        ll.addLayout(row)
        split.addWidget(left)

        card = Card("Conexión a PostgreSQL / PostGIS")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.name = QLineEdit()
        self.host = QLineEdit()
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(5432)
        self.port.setButtonSymbols(QSpinBox.NoButtons)
        self.port.setMaximumWidth(120)
        self.database = QLineEdit()
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.remember = QCheckBox("Recordar contraseña en el Administrador de credenciales de Windows")
        self.remember.setEnabled(keyring_available())
        form.addRow("Nombre:", self.name)
        form.addRow("Servidor:", self.host)
        form.addRow("Puerto:", self.port)
        form.addRow("Base de datos:", self.database)
        form.addRow("Usuario:", self.user)
        form.addRow("Contraseña:", self.password)
        form.addRow("", self.remember)
        card.body.addLayout(form)
        card.body.addWidget(hint("La base de datos se crea automáticamente al crear el primer esquema si no existe. "
                                 "Las contraseñas nunca se guardan en archivos de configuración."))
        self.result = Banner("info", "")
        card.body.addWidget(self.result)
        actions = QHBoxLayout()
        test = button("Probar conexión", "plug")
        test.clicked.connect(self._test)
        save = button("Guardar", "check", "primary")
        save.clicked.connect(self._save)
        actions.addStretch(1)
        actions.addWidget(test)
        actions.addWidget(save)
        card.body.addLayout(actions)
        card.body.addStretch(1)
        split.addWidget(card)
        split.setSizes([220, 600])
        lay.addWidget(split)
        self._current: str | None = None
        self.refresh()

    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for c in self.ctx.settings.connections:
            self.list.addItem(c.name)
        self.list.blockSignals(False)
        active = self.ctx.settings.active_connection
        items = self.list.findItems(active, Qt.MatchExactly) if active else []
        if items:
            self.list.setCurrentItem(items[0])
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self._new()

    def _load(self, name: str) -> None:
        prof = self.ctx.settings.connection(name) if name else None
        self._current = prof.name if prof else None
        self.result.set("info", "")
        if prof is None:
            return
        self.name.setText(prof.name)
        self.host.setText(prof.host)
        self.port.setValue(int(prof.port))
        self.database.setText(prof.database)
        self.user.setText(prof.user)
        self.password.setText(get_password(prof) or "")
        self.remember.setChecked(prof.save_password and keyring_available())
        self.delete.setEnabled(True)

    def _new(self) -> None:
        self._current = None
        self.list.clearSelection()
        self.name.setText("")
        self.host.setText("localhost")
        self.port.setValue(5432)
        self.database.setText("")
        self.user.setText("postgres")
        self.password.setText("")
        self.remember.setChecked(keyring_available())
        self.delete.setEnabled(False)
        self.result.set("info", "")
        self.name.setFocus()

    def _profile_from_form(self) -> ConnectionProfile:
        return ConnectionProfile(name=self.name.text().strip() or self.database.text().strip(),
                                 host=self.host.text().strip() or "localhost", port=self.port.value(),
                                 database=self.database.text().strip(), user=self.user.text().strip() or "postgres",
                                 save_password=self.remember.isChecked())

    def _save(self) -> None:
        prof = self._profile_from_form()
        if not prof.name or not prof.database:
            QMessageBox.warning(self, "Conexión", "Indique al menos el nombre y la base de datos.")
            return
        old = self.ctx.settings.connection(self._current) if self._current else None
        if old and old.secret_key != prof.secret_key:
            delete_password(old)
        if not prof.save_password:
            delete_password(prof)
        self.ctx.settings.upsert_connection(prof, old_name=self._current)
        set_password(prof, self.password.text())
        if not self.ctx.settings.active_connection or self.ctx.settings.active_connection == self._current:
            self.ctx.settings.active_connection = prof.name
        self._current = prof.name
        self.ctx.notify_settings()
        self.ctx.connectionChanged.emit()
        self.refresh()
        self.result.set("success", f"Conexión «{prof.name}» guardada.")

    def _delete(self) -> None:
        if not self._current:
            return
        if QMessageBox.question(self, "Eliminar", f"¿Eliminar la conexión «{self._current}»?") != QMessageBox.Yes:
            return
        prof = self.ctx.settings.connection(self._current)
        if prof:
            delete_password(prof)
        self.ctx.settings.connections = [c for c in self.ctx.settings.connections if c.name != self._current]
        if self.ctx.settings.active_connection == self._current:
            self.ctx.settings.active_connection = self.ctx.settings.connections[0].name if self.ctx.settings.connections else ""
        self.ctx.notify_settings()
        self.ctx.connectionChanged.emit()
        self.refresh()

    def _test(self) -> None:
        params = self._profile_from_form().params(self.password.text())
        self.result.set("info", f"Probando {params.describe()}...")

        def done(info):
            self._jobs.remove(job)
            parts = [f"Conexión correcta. PostgreSQL {info['server_version']}"]
            if info["database_exists"]:
                parts.append(f"PostGIS {info['postgis_version']}" if info["postgis_version"]
                             else "PostGIS no instalado en esta base (se instala al crear esquemas)")
            else:
                parts.append(f"la base de datos «{params.database}» no existe todavia (se creará)")
            kind = "success" if info["postgis_available"] else "warning"
            if not info["postgis_available"]:
                parts.append("<b>la extensión PostGIS no está disponible en el servidor</b>")
            self.result.set(kind, " · ".join(parts))

        def failed(tb):
            self._jobs.remove(job)
            self.result.set("error", "No se pudo conectar: " + tb.strip().splitlines()[-1].split(":", 1)[-1])

        job = Job(lambda: Database(params).test())
        self._jobs.append(job)
        job.finished.connect(done)
        job.failed.connect(failed)
        job.start()


# =========================================================== perfiles de modelo
class ModelProfilesTab(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._load)
        ll.addWidget(self.list, 1)
        row = QHBoxLayout()
        new = button("Nuevo", "plus")
        new.clicked.connect(self._new)
        dup = button("Duplicar", "copy")
        dup.clicked.connect(self._duplicate)
        self.delete = button("Eliminar", "trash", "danger")
        self.delete.clicked.connect(self._delete)
        row.addWidget(new)
        row.addWidget(dup)
        row.addWidget(self.delete)
        ll.addLayout(row)
        split.addWidget(left)

        host = QWidget()
        hl = QVBoxLayout(host)
        hl.setContentsMargins(0, 0, 6, 0)
        hl.setSpacing(12)
        general = Card("Perfil de modelo", "Agrupa la carpeta de modelos .ili, los modelos y las opciones de ili2pg.")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.name = QLineEdit()
        self.modeldir = PathEdit("dir", placeholder="Carpeta con los archivos .ili")
        self.modeldir.changed.connect(lambda _: self._scan())
        self.srs = QLineEdit()
        self.srs.setMaximumWidth(120)
        self.prescript = PathEdit("file", "Script SQL (*.sql)", placeholder="Opcional: script previo (ej. CTM12)")
        form.addRow("Nombre:", self.name)
        form.addRow("Carpeta de modelos:", self.modeldir)
        srs_row = QHBoxLayout()
        srs_row.addWidget(self.srs)
        srs_row.addWidget(label("9377 = MAGNA-SIRGAS / Origen-Nacional (CTM12)", "Muted"))
        srs_row.addStretch(1)
        form.addRow("Código EPSG:", srs_row)
        form.addRow("Script previo:", self.prescript)
        general.body.addLayout(form)
        hl.addWidget(general)

        models = Card("Modelos", "Marque los modelos para los que se crearán tablas. Los modelos de tipos "
                                 "(TYPE) se incluyen automáticamente como dependencias.")
        sug = button("Usar sugeridos", "check", "link")
        sug.clicked.connect(self._use_suggested)
        rescan = button("Releer carpeta", "refresh", "link")
        rescan.clicked.connect(self._scan)
        models.header_tools.addWidget(sug)
        models.header_tools.addWidget(rescan)
        self.models = QListWidget()
        self.models.setMinimumHeight(150)
        models.body.addWidget(self.models)
        self.models_banner = Banner("warning", "")
        models.body.addWidget(self.models_banner)
        hl.addWidget(models)

        opts = Card("Opciones de ili2pg", "Los valores por defecto son los recomendados para LADM-COL.")
        reset = button("Restaurar recomendadas", "refresh", "link")
        reset.clicked.connect(lambda: self._set_options(default_schema_options()))
        opts.header_tools.addWidget(reset)
        self.option_checks: dict[str, QCheckBox] = {}
        groups: dict[str, list] = {}
        for opt in SCHEMA_OPTIONS:
            groups.setdefault(opt.group, []).append(opt)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        for i, (group, items) in enumerate(groups.items()):
            box = QGroupBox(group)
            bl = QVBoxLayout(box)
            for opt in items:
                chk = QCheckBox(opt.label)
                chk.setToolTip(f"--{opt.flag}\n{opt.description}")
                self.option_checks[opt.flag] = chk
                bl.addWidget(chk)
            bl.addStretch(1)
            grid.addWidget(box, i // 2, i % 2)
        opts.body.addLayout(grid)
        self.option_checks["createBasketCol"].toggled.connect(self._basket_warning)
        self.basket_banner = Banner("warning", "")
        opts.body.addWidget(self.basket_banner)
        hl.addWidget(opts)

        actions = QHBoxLayout()
        actions.addStretch(1)
        save = button("Guardar perfil", "check", "primary")
        save.clicked.connect(self._save)
        actions.addWidget(save)
        hl.addLayout(actions)
        hl.addStretch(1)
        split.addWidget(_scroll(host))
        split.setSizes([220, 700])
        lay.addWidget(split)
        self._current: str | None = None
        self._scanned = []
        self.refresh()

    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for m in self.ctx.settings.model_profiles:
            self.list.addItem(m.name)
        self.list.blockSignals(False)
        active = self.ctx.settings.active_model_profile
        items = self.list.findItems(active, Qt.MatchExactly) if active else []
        if items:
            self.list.setCurrentItem(items[0])
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self._new()

    def _load(self, name: str) -> None:
        prof = self.ctx.settings.model_profile(name) if name else None
        if prof is None:
            return
        self._current = prof.name
        self.name.setText(prof.name)
        self.modeldir.setText(prof.modeldir)
        self.srs.setText(prof.srs_code)
        self.prescript.setText(prof.prescript)
        self._set_options(prof.normalized_options())
        self._scan(selected=prof.models)
        self.delete.setEnabled(True)

    def _new(self) -> None:
        self._current = None
        self.list.clearSelection()
        self.name.setText("")
        self.modeldir.setText("")
        self.srs.setText("9377")
        ctm = paths.default_ctm12_script()
        self.prescript.setText(str(ctm) if ctm.exists() else "")
        self._set_options(default_schema_options())
        self._scan(selected=[])
        self.delete.setEnabled(False)
        self.name.setFocus()

    def _duplicate(self) -> None:
        self._current = None
        self.name.setText(self.name.text() + " (copia)")
        self.delete.setEnabled(False)

    def _set_options(self, opts: dict) -> None:
        for flag, chk in self.option_checks.items():
            chk.setChecked(bool(opts.get(flag)))
        self._basket_warning()

    def _basket_warning(self) -> None:
        on = self.option_checks["createBasketCol"].isChecked()
        self.basket_banner.set("warning", "" if on else
                               "Sin <b>columna de basket</b> no se puede crear un esquema SINIC ni Interno ACC "
                               "(ili2pg lo exige) y no se podrán reemplazar datos al importar.")

    def _selected_models(self) -> list[str]:
        return [self.models.item(i).data(Qt.UserRole) for i in range(self.models.count())
                if self.models.item(i).checkState() == Qt.Checked]

    def _scan(self, selected: list[str] | None = None) -> None:
        if selected is None:
            selected = self._selected_models()
        folder = self.modeldir.text()
        self._scanned = scan_model_dir(folder) if folder else []
        self.models.clear()
        seen = set()
        for m in self._scanned:
            if m.name in seen:
                continue
            seen.add(m.name)
            kind = f" [{m.kind}]" if m.kind else ""
            item = QListWidgetItem(f"{m.name}{kind}   v{m.version or '?'}   ·   {Path(m.file).name}")
            item.setData(Qt.UserRole, m.name)
            item.setToolTip("Importa: " + (", ".join(m.imports) or "(ninguno)"))
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked if m.name in selected else Qt.Unchecked)
            self.models.addItem(item)
        msgs = []
        if folder and not self._scanned:
            msgs.append("No se encontraron modelos INTERLIS en la carpeta.")
        for name, files in duplicate_models(self._scanned).items():
            msgs.append(f"El modelo <b>{name}</b> está definido en varios archivos: "
                        + ", ".join(Path(f).name for f in files) + ". Deje solo uno para evitar ambigüedades.")
        missing = [s for s in selected if s not in seen]
        if missing and folder:
            msgs.append("Modelos del perfil que no están en la carpeta: " + ", ".join(missing))
        self.models_banner.set("warning", "<br>".join(msgs))

    def _use_suggested(self) -> None:
        sug = set(suggested_models(self._scanned))
        for i in range(self.models.count()):
            it = self.models.item(i)
            it.setCheckState(Qt.Checked if it.data(Qt.UserRole) in sug else Qt.Unchecked)

    def _save(self) -> None:
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Perfil", "Indique un nombre para el perfil.")
            return
        models = self._selected_models()
        if not models:
            QMessageBox.warning(self, "Perfil", "Seleccione al menos un modelo.")
            return
        prof = ModelProfile(name=name, modeldir=self.modeldir.text(), models=models,
                            srs_code=self.srs.text().strip() or "9377",
                            options={f: c.isChecked() for f, c in self.option_checks.items()},
                            prescript=self.prescript.text())
        self.ctx.settings.upsert_model_profile(prof, old_name=self._current)
        if not self.ctx.settings.active_model_profile or self.ctx.settings.active_model_profile == self._current:
            self.ctx.settings.active_model_profile = name
        self._current = name
        self.ctx.notify_settings()
        self.ctx.profileChanged.emit()
        self.refresh()

    def _delete(self) -> None:
        if not self._current:
            return
        if QMessageBox.question(self, "Eliminar", f"¿Eliminar el perfil «{self._current}»?") != QMessageBox.Yes:
            return
        s = self.ctx.settings
        s.model_profiles = [m for m in s.model_profiles if m.name != self._current]
        if s.active_model_profile == self._current:
            s.active_model_profile = s.model_profiles[0].name if s.model_profiles else ""
        self.ctx.notify_settings()
        self.ctx.profileChanged.emit()
        self.refresh()


# ================================================================ herramientas
class ToolsTab(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        tools = Card("Herramientas", "Deje en blanco para usar las versiones fijadas (ili2pg 5.5.1 e ilivalidator 1.15.0) descargadas en la carpeta ili2pg/.")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.java = PathEdit("file", "Java (java.exe)", placeholder="Detectar automáticamente")
        self.java_info = label("", "Muted")
        self.ili2pg = PathEdit("file", "JAR (*.jar)", placeholder=str(paths.default_ili2pg_jar()))
        self.ilivalidator = PathEdit("file", "JAR (*.jar)", placeholder=str(paths.default_ilivalidator_jar()))
        self.memory = QComboBox()
        self.memory.addItems(["Automática", "2g", "4g", "6g", "8g", "12g"])
        form.addRow("Java:", self.java)
        form.addRow("", self.java_info)
        form.addRow("ili2pg:", self.ili2pg)
        form.addRow("ilivalidator:", self.ilivalidator)
        form.addRow("Memoria máxima Java:", self.memory)
        tools.body.addLayout(form)
        tools.body.addWidget(hint("Aumente la memoria si procesa archivos XTF muy grandes (cientos de MB)."))
        lay.addWidget(tools)

        general = Card("General")
        gform = QFormLayout()
        gform.setLabelAlignment(Qt.AlignRight)
        self.prefix = QLineEdit()
        self.prefix.setMaximumWidth(140)
        self.log_dir = PathEdit("dir", placeholder=str(paths.default_log_dir()))
        self.theme = QComboBox()
        self.theme.addItem("Según el sistema", "sistema")
        self.theme.addItem("Claro", "claro")
        self.theme.addItem("Oscuro", "oscuro")
        gform.addRow("Prefijo de esquemas:", self.prefix)
        gform.addRow("", label("Esquema por municipio = prefijo + código DIVIPOLA (ej. cun25279)", "Muted"))
        gform.addRow("Carpeta de logs:", self.log_dir)
        gform.addRow("Tema:", self.theme)
        general.body.addLayout(gform)
        lay.addWidget(general)

        legacy = Card("Migrar desde la versión 2.0",
                      "Importa las conexiones y modelos guardados por la versión anterior (Tkinter). "
                      "Las contraseñas se trasladan al Administrador de credenciales de Windows.")
        mig = button("Importar perfiles de la versión 2.0", "import")
        mig.setEnabled(legacy_profiles_available())
        mig.clicked.connect(self._migrate)
        legacy.body.addWidget(mig, 0, Qt.AlignLeft)
        lay.addWidget(legacy)

        actions = QHBoxLayout()
        actions.addStretch(1)
        save = button("Guardar", "check", "primary")
        save.clicked.connect(self._save)
        actions.addWidget(save)
        lay.addLayout(actions)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll(host))
        self.load()

    def load(self) -> None:
        s = self.ctx.settings
        self.java.setText(s.tools.java)
        self.ili2pg.setText(s.tools.ili2pg_jar)
        self.ilivalidator.setText(s.tools.ilivalidator_jar)
        idx = self.memory.findText(s.tools.java_max_memory) if s.tools.java_max_memory else 0
        self.memory.setCurrentIndex(max(idx, 0))
        self.prefix.setText(s.schema_prefix)
        self.log_dir.setText(s.log_dir)
        self.theme.setCurrentIndex(max(self.theme.findData(s.ui.get("theme", "sistema")), 0))
        self._detect_java()

    def _detect_java(self) -> None:
        java = paths.find_java(self.java.text())
        if not java:
            self.java_info.setText("<span style='color:#c0352b'>No se encontró Java. Instale Java 8 o superior.</span>")
            return
        ver = java_version(java)
        self.java_info.setText(f"Detectado: {java}  (versión {ver or 'desconocida'})")

    def _save(self) -> None:
        s = self.ctx.settings
        prefix = self.prefix.text().strip().lower()
        if prefix and validate_identifier(prefix + "x"):
            QMessageBox.warning(self, "Prefijo", "El prefijo solo puede tener minúsculas, números y guion bajo.")
            return
        s.tools.java = self.java.text()
        s.tools.ili2pg_jar = self.ili2pg.text()
        s.tools.ilivalidator_jar = self.ilivalidator.text()
        s.tools.java_max_memory = "" if self.memory.currentIndex() == 0 else self.memory.currentText()
        s.schema_prefix = prefix
        s.log_dir = self.log_dir.text()
        theme_changed = s.ui.get("theme", "sistema") != self.theme.currentData()
        s.ui["theme"] = self.theme.currentData()
        self.ctx.notify_settings()
        self._detect_java()
        if theme_changed:
            QMessageBox.information(self, "Tema", "El cambio de tema se aplicará al reiniciar la aplicación.")

    def _migrate(self) -> None:
        n_conn, n_models = import_legacy_profiles(self.ctx.settings)
        self.ctx.notify_settings()
        self.ctx.connectionChanged.emit()
        self.ctx.profileChanged.emit()
        QMessageBox.information(self, "Migración", f"Se importaron {n_conn} conexión(es) y {n_models} perfil(es) de modelo.")
        win = self.window()
        if hasattr(win, "settings_page"):
            win.settings_page.reload()


class SettingsPage(Page):
    key = "settings"
    title = "Configuración"
    subtitle = "Conexiones, perfiles de modelo y herramientas."

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        self.tabs = QTabWidget()
        self.connections = ConnectionsTab(ctx)
        self.profiles = ModelProfilesTab(ctx)
        self.tools = ToolsTab(ctx)
        self.tabs.addTab(self.connections, "Conexiones")
        self.tabs.addTab(self.profiles, "Perfiles de modelo")
        self.tabs.addTab(self.tools, "Herramientas y general")
        lay.addWidget(self.tabs)

    def reload(self) -> None:
        self.connections.refresh()
        self.profiles.refresh()
        self.tools.load()

    def receive(self, payload: dict) -> None:
        tab = payload.get("tab")
        if tab is not None:
            self.tabs.setCurrentIndex(tab)
