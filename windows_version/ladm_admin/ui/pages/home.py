"""Inicio: estado del entorno y flujo de trabajo."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ...core import paths
from ...core.database import Database
from ...core.process import java_version
from ...core.settings import legacy_profiles_available
from ...core.tools_setup import install_missing, missing_packages
from .. import theme
from ..icons import dot, icon
from ..widgets import Banner, Card, button, hint, label
from ..worker import Job
from .base import Page

STEPS = [
    ("validate", "shield", "Validar XTF",
     "Revise los archivos de transferencia con ilivalidator. Vea los errores en una tabla filtrable."),
    ("create", "database", "Crear esquema",
     "Genere la estructura LADM-COL en PostgreSQL: un esquema por municipio o un esquema único con datasets."),
    ("import", "import", "Importar XTF",
     "Cargue los datos en los esquemas creados. Detecta conflictos y permite reemplazar, agregar u omitir."),
    ("export", "export", "Exportar XTF",
     "Genere los archivos XTF por municipio desde la base de datos, listos para validar y entregar."),
]


class HomePage(Page):
    key = "home"
    title = "Inicio"
    subtitle = "Flujo recomendado: validar → crear esquema → importar → exportar."

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self._jobs: list[Job] = []
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        self.legacy = Banner("info", "")
        self.legacy.action.setText("Importar perfiles →")
        self.legacy.action.show()
        self.legacy.action.clicked.connect(self._go_legacy)
        lay.addWidget(self.legacy)

        self.tools_banner = Banner("warning", "")
        self.tools_banner.action.setText("Descargar herramientas")
        self.tools_banner.action.show()
        self.tools_banner.action.clicked.connect(self._download_tools)
        lay.addWidget(self.tools_banner)

        grid = QGridLayout()
        grid.setSpacing(14)
        t = theme.tokens()
        for i, (key, ic, title, desc) in enumerate(STEPS):
            card = Card()
            head = QHBoxLayout()
            num = label(str(i + 1), "StepNumber")
            head.addWidget(num)
            pic = QLabel()
            pic.setPixmap(icon(ic, t.primary).pixmap(22, 22))
            head.addWidget(pic)
            head.addWidget(label(title, "CardTitle"), 1)
            card.body.addLayout(head)
            card.body.addWidget(hint(desc))
            go = button("Abrir", variant="link")
            go.clicked.connect(lambda _=False, k=key: self.ctx.navigateRequested.emit(k))
            card.body.addWidget(go, 0, Qt.AlignRight)
            grid.addWidget(card, i // 2, i % 2)
        lay.addLayout(grid)

        env = Card("Estado del entorno", "Se verifica al abrir la aplicación.")
        refresh = button("Verificar de nuevo", "refresh", "link")
        refresh.clicked.connect(self.check_environment)
        env.header_tools.addWidget(refresh)
        self.env_rows: dict[str, tuple[QLabel, QLabel]] = {}
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        for r, (key, text) in enumerate((("java", "Java"), ("ili2pg", "ili2pg"), ("ilivalidator", "ilivalidator"),
                                         ("db", "Base de datos"), ("profile", "Perfil de modelo"))):
            ic = QLabel()
            name = label(text)
            name.setMinimumWidth(130)
            val = label("...", "Muted", wrap=True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addWidget(ic, r, 0)
            form.addWidget(name, r, 1)
            form.addWidget(val, r, 2)
            self.env_rows[key] = (ic, val)
        form.setColumnStretch(2, 1)
        env.body.addLayout(form)
        cfg = button("Ir a Configuración", "settings", "link")
        cfg.clicked.connect(lambda: self.ctx.navigateRequested.emit("settings"))
        env.body.addWidget(cfg, 0, Qt.AlignRight)
        lay.addWidget(env)
        lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(host)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.ctx.connectionChanged.connect(self.check_environment)
        self.ctx.profileChanged.connect(self.check_environment)
        self.ctx.settingsChanged.connect(self.check_environment)
        self.check_environment()

    def _download_tools(self) -> None:
        self.tools_banner.action.setEnabled(False)
        self.tools_banner.set("info", "Descargando herramientas desde downloads.interlis.ch ...")

        def done(_):
            self._jobs.remove(job)
            self.tools_banner.action.setEnabled(True)
            self.check_environment()

        def failed(tb):
            self._jobs.remove(job)
            self.tools_banner.action.setEnabled(True)
            self.tools_banner.set("error", "No se pudo descargar: " + tb.strip().splitlines()[-1])

        job = Job(install_missing, None, lambda _msg: None)
        self._jobs.append(job)
        job.finished.connect(done)
        job.failed.connect(failed)
        job.start()

    def _set(self, key: str, ok: bool | None, text: str) -> None:
        t = theme.tokens()
        color = t.text_muted if ok is None else (t.success if ok else t.error)
        ic, val = self.env_rows[key]
        ic.setPixmap(dot(color).pixmap(12, 12))
        val.setText(text)

    def _go_legacy(self) -> None:
        self.ctx.navigateRequested.emit("settings")
        win = self.window()
        if hasattr(win, "deliver"):
            win.deliver("settings", {"tab": 2})

    def check_environment(self) -> None:
        s = self.ctx.settings
        self.legacy.set("info", "Se encontraron perfiles de la versión 2.0. Puede importar sus conexiones y modelos."
                        if legacy_profiles_available() and not s.connections else "")
        tools = s.tools.resolve()
        missing = [p for p in missing_packages()
                   if (p.name == "ili2pg" and not s.tools.ili2pg_jar)
                   or (p.name == "ilivalidator" and not s.tools.ilivalidator_jar)]
        self.tools_banner.set("warning", "Faltan " + " y ".join(f"<b>{p.name} {p.version}</b>" for p in missing)
                              + ". Se descargan del sitio oficial de INTERLIS (requiere internet)." if missing else "")
        for key, jar in (("ili2pg", tools.ili2pg_jar), ("ilivalidator", tools.ilivalidator_jar)):
            exists = Path(jar).is_file()
            self._set(key, exists, jar if exists else f"No encontrado: {jar}")
        prof = self.ctx.model_profile()
        if prof:
            ok = bool(prof.models) and Path(prof.modeldir).is_dir()
            self._set("profile", ok, f"{prof.name}: {len(prof.models)} modelo(s) en {prof.modeldir}")
        else:
            self._set("profile", False, "No hay perfiles de modelo. Cree uno en Configuración.")

        java = paths.find_java(s.tools.java)
        self._set("java", None, "Verificando...")
        conn = self.ctx.connection_profile()
        self._set("db", None, "Verificando..." if conn else "")

        def check():
            result = {"java": java_version(java) if java else None}
            if conn:
                params = self.ctx.connection_params(ask=False)
                try:
                    if params is None or not params.password:
                        raise RuntimeError("contraseña no guardada (se pedirá al ejecutar)")
                    result["db"] = Database(params).test()
                except Exception as exc:  # noqa: BLE001 - se muestra al usuario
                    result["db_error"] = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            return result

        def done(res):
            self._jobs.remove(job)
            if java and res["java"]:
                self._set("java", True, f"Java {res['java']} · {java}")
            else:
                self._set("java", False, "No se encontró Java (instale Java 8 o superior)")
            if not conn:
                self._set("db", False, "No hay conexiones. Configure una en Configuración.")
            elif "db" in res:
                info = res["db"]
                text = f"{conn.name} · {conn.secret_key} · PostgreSQL {info['server_version']}"
                if not info["database_exists"]:
                    text += " (la base de datos se creará)"
                self._set("db", True, text)
            else:
                self._set("db", None if "contraseña" in res.get("db_error", "") else False,
                          f"{conn.name}: {res.get('db_error')}")

        job = Job(check)
        self._jobs.append(job)
        job.finished.connect(done)
        job.failed.connect(lambda tb: (self._jobs.remove(job), self._set("db", False, tb.strip().splitlines()[-1])))
        job.start()
