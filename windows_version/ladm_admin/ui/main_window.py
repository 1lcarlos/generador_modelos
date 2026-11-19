"""Ventana principal: barra lateral, encabezado con contexto y paginas."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import APP_NAME, APP_ORG, __version__
from . import theme
from .context import AppContext
from .icons import icon
from .pages.base import OperationPage, Page
from .pages.create import CreatePage
from .pages.export import ExportPage
from .pages.home import HomePage
from .pages.import_ import ImportPage
from .pages.settings import SettingsPage
from .pages.validate import ValidatePage
from .widgets import label

NAV = [
    (None, None, None),
    ("home", "home", "Inicio"),
    (None, "FLUJO DE TRABAJO", None),
    ("validate", "shield", "1  Validar XTF"),
    ("create", "database", "2  Crear esquema"),
    ("import", "import", "3  Importar XTF"),
    ("export", "export", "4  Exportar XTF"),
    (None, "SISTEMA", None),
    ("settings", "settings", "Configuración"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1280, 860)
        self.setMinimumSize(1050, 700)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self._build_header())
        self.stack = QStackedWidget()
        rl.addWidget(self.stack, 1)
        root.addWidget(right, 1)
        self.setCentralWidget(central)

        self.pages: dict[str, Page] = {}
        for cls in (HomePage, ValidatePage, CreatePage, ImportPage, ExportPage, SettingsPage):
            page = cls(ctx)
            self.pages[page.key] = page
            self.stack.addWidget(page)
        self.settings_page = self.pages["settings"]

        self.statusBar().showMessage("Listo")
        ctx.navigateRequested.connect(self.go)
        ctx.settingsChanged.connect(self._refresh_context)
        ctx.connectionChanged.connect(self._refresh_context)
        ctx.profileChanged.connect(self._refresh_context)
        ctx.busyChanged.connect(self._on_busy)
        self._refresh_context()
        self.go(ctx.settings.ui.get("last_page", "home"))

    # ------------------------------------------------------------- layout
    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 18, 0, 12)
        lay.setSpacing(0)
        brand = QVBoxLayout()
        brand.setContentsMargins(18, 0, 18, 8)
        brand.addWidget(label("Administrador LADM-COL", "Brand"))
        brand.addWidget(label(APP_ORG, "BrandSub", wrap=True))
        lay.addLayout(brand)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setFocusPolicy(Qt.NoFocus)
        self._nav_rows: dict[str, int] = {}
        for key, ic, text in NAV:
            if key is None:
                item = QListWidgetItem(ic or "")
                item.setFlags(Qt.NoItemFlags)
                item.setSizeHint(QSize(0, 30 if ic else 8))
                font = item.font()
                font.setPointSizeF(7.5)
                font.setBold(True)
                item.setFont(font)
                item.setForeground(Qt.gray)
                self.nav.addItem(item)
                continue
            item = QListWidgetItem(icon(ic, "#c9d4e5"), text)
            item.setData(Qt.UserRole, key)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
            self._nav_rows[key] = self.nav.count() - 1
        self.nav.currentItemChanged.connect(self._on_nav)
        lay.addWidget(self.nav, 1)
        lay.addWidget(label(f"   Versión {__version__} · ili2pg 5.5.1", "Version"))
        return side

    def _build_header(self) -> QWidget:
        head = QFrame()
        head.setObjectName("Header")
        lay = QHBoxLayout(head)
        lay.setContentsMargins(22, 12, 22, 12)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.page_title = label("", "PageTitle")
        self.page_subtitle = label("", "PageSubtitle")
        col.addWidget(self.page_title)
        col.addWidget(self.page_subtitle)
        lay.addLayout(col, 1)

        def ctx_box(caption: str, combo: QComboBox, extra: QWidget | None = None) -> QVBoxLayout:
            box = QVBoxLayout()
            box.setSpacing(2)
            box.addWidget(label(caption, "ContextLabel"))
            row = QHBoxLayout()
            row.setSpacing(6)
            if extra:
                row.addWidget(extra)
            row.addWidget(combo)
            box.addLayout(row)
            return box

        self.conn_dot = QLabel()
        self.conn_combo = QComboBox()
        self.conn_combo.setMinimumWidth(230)
        self.conn_combo.setToolTip("Conexión activa: se usa para crear, importar y exportar")
        self.conn_combo.activated.connect(lambda _: self._pick_connection())
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.setToolTip("Perfil de modelo activo: modelos .ili y opciones de ili2pg")
        self.profile_combo.activated.connect(lambda _: self.ctx.set_active_profile(self.profile_combo.currentText()))
        lay.addLayout(ctx_box("BASE DE DATOS", self.conn_combo, self.conn_dot))
        lay.addSpacing(14)
        lay.addLayout(ctx_box("PERFIL DE MODELO", self.profile_combo))
        return head

    # --------------------------------------------------------- navegacion
    def go(self, key: str) -> None:
        if key not in self.pages:
            key = "home"
        row = self._nav_rows.get(key)
        if row is not None and self.nav.currentRow() != row:
            self.nav.setCurrentRow(row)
        else:
            self._show(key)

    def deliver(self, key: str, payload: dict) -> None:
        self.go(key)
        self.pages[key].receive(payload)

    def _on_nav(self, current: QListWidgetItem, _previous) -> None:
        if current is not None and current.data(Qt.UserRole):
            self._show(current.data(Qt.UserRole))

    def _show(self, key: str) -> None:
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        self.page_title.setText(page.title)
        self.page_subtitle.setText(page.subtitle)
        self.ctx.settings.ui["last_page"] = key
        page.on_shown()

    # ------------------------------------------------------------ contexto
    def _refresh_context(self) -> None:
        s = self.ctx.settings
        t = theme.tokens()
        self.conn_combo.blockSignals(True)
        self.conn_combo.clear()
        for c in s.connections:
            self.conn_combo.addItem(c.name)
            self.conn_combo.setItemData(self.conn_combo.count() - 1, c.secret_key, Qt.ToolTipRole)
        if not s.connections:
            self.conn_combo.addItem("Sin conexiones · configurar")
        else:
            self.conn_combo.setCurrentText(s.active_connection or s.connections[0].name)
            if not s.active_connection:
                s.active_connection = s.connections[0].name
        self.conn_combo.blockSignals(False)
        prof = self.ctx.connection_profile()
        self.conn_dot.setPixmap(icon("database", t.primary if prof else t.text_muted).pixmap(18, 18))
        self.conn_dot.setToolTip(prof.secret_key if prof else "")

        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for m in s.model_profiles:
            self.profile_combo.addItem(m.name)
        if s.model_profiles:
            self.profile_combo.setCurrentText(s.active_model_profile or s.model_profiles[0].name)
            if not s.active_model_profile:
                s.active_model_profile = s.model_profiles[0].name
        else:
            self.profile_combo.addItem("Sin perfiles · configurar")
        self.profile_combo.blockSignals(False)

    def _pick_connection(self) -> None:
        if not self.ctx.settings.connections:
            self.go("settings")
            return
        self.ctx.set_active_connection(self.conn_combo.currentText())

    def _on_busy(self, busy: bool) -> None:
        self.conn_combo.setEnabled(not busy)
        self.profile_combo.setEnabled(not busy)
        self.statusBar().showMessage("Proceso en ejecución..." if busy else "Listo")

    # --------------------------------------------------------------- cierre
    def closeEvent(self, event) -> None:
        if self.ctx.busy:
            answer = QMessageBox.question(self, "Proceso en curso",
                                          "Hay un proceso en ejecución. Si sale, se detendrá.\n¿Desea salir?")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        for page in self.pages.values():
            if isinstance(page, OperationPage):
                page.shutdown()
        self.ctx.save()
        event.accept()
