"""Dialogos: contraseña, esquema existente, conflicto de importación y errores de validación."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QRadioButton,
    QVBoxLayout, QWidget,
)

from ..core.database import SchemaInfo
from ..core.ili2db import ImportMode
from ..core.operations import ExistingSchemaAction, ImportItem
from ..core.reports import read_validation_csv
from ..core.settings import ConnectionProfile, keyring_available
from . import theme
from .icons import icon
from .widgets import DataTable, button, hint, label, open_path


class PasswordDialog(QDialog):
    def __init__(self, profile: ConnectionProfile, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Contraseña de la base de datos")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.addWidget(label(f"Conexión <b>{profile.name}</b><br>{profile.secret_key}", wrap=True))
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        self.edit.setPlaceholderText("Contraseña")
        lay.addWidget(self.edit)
        self.chk = QCheckBox("Recordar en el Administrador de credenciales de Windows")
        self.chk.setChecked(profile.save_password and keyring_available())
        self.chk.setEnabled(keyring_available())
        lay.addWidget(self.chk)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def password(self) -> str:
        return self.edit.text()

    def remember(self) -> bool:
        return self.chk.isChecked()


class _ChoiceDialog(QDialog):
    """Diálogo con opciones excluyentes + 'aplicar a todos'."""

    def __init__(self, title: str, intro: str, details: list[tuple[str, str]],
                 choices: list[tuple[object, str, str]], default, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        head = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(icon("alert", theme.tokens().warning).pixmap(28, 28))
        head.addWidget(ic, 0, Qt.AlignTop)
        head.addWidget(label(intro, wrap=True), 1)
        lay.addLayout(head)
        if details:
            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignRight)
            for k, v in details:
                val = label(v, wrap=True)
                val.setTextInteractionFlags(Qt.TextSelectableByMouse)
                form.addRow(label(k, "Muted"), val)
            lay.addLayout(form)
        self._radios: list[tuple[QRadioButton, object]] = []
        for value, text, desc in choices:
            rb = QRadioButton(text)
            rb.setChecked(value == default)
            lay.addWidget(rb)
            if desc:
                h = hint(desc)
                h.setContentsMargins(26, 0, 0, 4)
                lay.addWidget(h)
            self._radios.append((rb, value))
        self.apply_all = QCheckBox("Aplicar esta decisión a los demas casos de este proceso")
        lay.addWidget(self.apply_all)
        bb = QDialogButtonBox()
        ok = bb.addButton("Continuar", QDialogButtonBox.AcceptRole)
        ok.setProperty("variant", "primary")
        bb.addButton("Detener el proceso", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def choice(self):
        return next((v for rb, v in self._radios if rb.isChecked()), None)


def ask_existing_schema(info: SchemaInfo, parent: QWidget | None = None) -> tuple[ExistingSchemaAction, bool]:
    details = [
        ("Esquema", info.name),
        ("Creado con", info.ili2db_version and f"ili2pg {info.ili2db_version}" or ("no es un esquema ili2db" if not info.is_ili2db else "desconocido")),
        ("Tablas", str(info.table_count)),
        ("Datos", ", ".join(info.datasets) if info.datasets else ("con datos" if info.has_data else "sin datos")),
    ]
    dlg = _ChoiceDialog(
        "Esquema existente",
        f"El esquema <b>{info.name}</b> ya existe en la base de datos. ¿Qué desea hacer?",
        details,
        [
            (ExistingSchemaAction.SKIP, "Omitir", "No se modifica el esquema."),
            (ExistingSchemaAction.UPDATE, "Actualizar estructura",
             "Ejecuta ili2pg sobre el esquema existente (agrega modelos/tablas). Conserva los datos."),
            (ExistingSchemaAction.RECREATE, "Recrear",
             "Borra el esquema y sus datos y lo crea de nuevo. Si la creación falla, se restaura el original."),
        ],
        ExistingSchemaAction.SKIP, parent,
    )
    if not dlg.exec():
        return ExistingSchemaAction.ABORT, False
    return dlg.choice(), dlg.apply_all.isChecked()


def ask_import_conflict(item: ImportItem, parent: QWidget | None = None) -> tuple[ImportMode | None, bool]:
    info = item.schema_info
    datasets = ", ".join(info.datasets) if info and info.datasets else "(sin nombre de dataset)"
    can_replace = bool(info and info.basket_col)
    choices = [
        (ImportMode.CANCEL, "No importar este archivo", "El destino queda como esta."),
        (ImportMode.REPLACE, "Reemplazar los datos existentes",
         "Borra los datos del municipio en el destino e importa el archivo, todo en una transacción."
         if can_replace else "No disponible: el esquema no tiene columna de basket."),
        (ImportMode.APPEND, "Agregar como un nuevo dataset",
         "Conserva los datos actuales. Puede fallar si el archivo repite objetos ya cargados."),
    ]
    dlg = _ChoiceDialog(
        "El destino ya tiene datos",
        f"El archivo <b>{item.source.display}</b> se importaria en <b>{item.schema}</b>, que ya contiene datos.",
        [("Esquema", item.schema), ("Dataset del archivo", item.dataset or "-"), ("Datasets existentes", datasets)],
        choices, ImportMode.CANCEL, parent,
    )
    if not can_replace:
        dlg._radios[1][0].setEnabled(False)
    if not dlg.exec():
        return None, False
    return dlg.choice(), dlg.apply_all.isChecked()


class IssuesDialog(QDialog):
    """Errores y advertencias de ilivalidator en una tabla filtrable."""

    def __init__(self, title: str, csv_path: str, log_path: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Resultados de validación - {title}")
        self.resize(1100, 600)
        self.issues = read_validation_csv(csv_path)
        lay = QVBoxLayout(self)
        n_err = sum(1 for i in self.issues if i.type == "Error")
        n_warn = len(self.issues) - n_err
        lay.addWidget(label(f"<b>{title}</b> &nbsp; {n_err} errores, {n_warn} advertencias", wrap=True))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtrar por texto, clase o TID...")
        self.search.setClearButtonEnabled(True)
        self.kind = QComboBox()
        self.kind.addItems(["Errores y advertencias", "Solo errores", "Solo advertencias"])
        bar.addWidget(self.search, 1)
        bar.addWidget(self.kind)
        lay.addLayout(bar)
        self.table = DataTable(["Tipo", "Mensaje", "Clase", "TID", "Línea", "X", "Y"], stretch_col=1)
        for col, w in ((0, 90), (2, 260), (3, 250), (4, 60), (5, 90), (6, 90)):
            self.table.setColumnWidth(col, w)
        self.table.setSortingEnabled(True)
        lay.addWidget(self.table, 1)
        self.count = label("", "Muted")
        bottom = QHBoxLayout()
        bottom.addWidget(self.count, 1)
        copy = button("Copiar tabla", "copy")
        copy.clicked.connect(self._copy)
        bottom.addWidget(copy)
        if log_path and Path(log_path).exists():
            b = button("Abrir log completo", "log")
            b.clicked.connect(lambda: open_path(log_path))
            bottom.addWidget(b)
        if Path(csv_path).exists():
            b = button("Abrir CSV", "file")
            b.clicked.connect(lambda: open_path(csv_path))
            bottom.addWidget(b)
        close = button("Cerrar")
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        lay.addLayout(bottom)
        self.search.textChanged.connect(self._fill)
        self.kind.currentIndexChanged.connect(self._fill)
        self._fill()

    def _visible(self):
        text = self.search.text().lower().strip()
        kind = self.kind.currentIndex()
        for i in self.issues:
            if kind == 1 and i.type != "Error":
                continue
            if kind == 2 and i.type != "Warning":
                continue
            if text and text not in f"{i.message} {i.class_name} {i.tid}".lower():
                continue
            yield i

    def _fill(self) -> None:
        t = theme.tokens()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        rows = list(self._visible())[:20000]
        self.table.setRowCount(len(rows))
        for r, i in enumerate(rows):
            it = self.table.set_text(r, 0, "Error" if i.type == "Error" else "Advertencia")
            it.setForeground(Qt.GlobalColor.red if i.type == "Error" else Qt.GlobalColor.darkYellow)
            self.table.set_text(r, 1, i.message, tooltip=i.message)
            self.table.set_text(r, 2, i.class_name, tooltip=i.class_name)
            self.table.set_text(r, 3, i.tid)
            self.table.set_text(r, 4, i.line)
            self.table.set_text(r, 5, i.x)
            self.table.set_text(r, 6, i.y)
        self.table.setSortingEnabled(True)
        self.count.setText(f"Mostrando {len(rows)} de {len(self.issues)}")
        _ = t

    def _copy(self) -> None:
        lines = ["\t".join(["Tipo", "Mensaje", "Clase", "TID", "Línea", "X", "Y"])]
        lines += ["\t".join([i.type, i.message, i.class_name, i.tid, i.line, i.x, i.y]) for i in self._visible()]
        QGuiApplication.clipboard().setText("\n".join(lines))
