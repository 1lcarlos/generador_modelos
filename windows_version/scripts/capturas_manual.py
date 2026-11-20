"""Regenera las capturas de docs/img recorriendo la aplicación con datos de ejemplo.

Uso (desde windows_version/):

    set LADM_PGPASSWORD=...
    python scripts/capturas_manual.py --ejemplos D:/ejemplos --salida ../docs/img [--port 5432]

Requisitos:
- La base de datos indicada (por defecto ``catastro``) NO debe existir: el script la crea al crear los
  esquemas y nunca reutiliza una base existente, para no tocar datos reales. Bórrela al terminar.
- La carpeta de ejemplos debe contener XTF del modelo SINIC con estos nombres:
    25279.xtf, 25645.xtf (válidos), 25019.xtf (municipio sin esquema, queda bloqueado)
  y 25436.xtf de otro modelo (muestra un error de validación).
- Para que las capturas no muestren rutas personales, ejecute el script desde una copia de la aplicación
  en una ruta neutra (p. ej. C:/LADMAdmin con ladm_admin/, Modelos/, ctm12/ e ili2pg/).

La configuración se guarda en un archivo temporal; no se modifica la del usuario.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

ARCHIVOS = {"valido": "25279.xtf", "valido2": "25645.xtf", "sin_esquema": "25019.xtf", "otro_modelo": "25436.xtf"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ejemplos", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--database", default="catastro")
    args = ap.parse_args()

    password = os.environ.get("LADM_PGPASSWORD")
    if not password:
        print("Defina LADM_PGPASSWORD con la contraseña de PostgreSQL")
        return 2
    faltan = [n for n in ARCHIVOS.values() if not (args.ejemplos / n).is_file()]
    if faltan:
        print("Faltan archivos de ejemplo:", ", ".join(faltan))
        return 2

    import ladm_admin.core.settings as st
    from ladm_admin.core.database import ConnectionParams, Database

    if Database(ConnectionParams(args.host, args.port, args.database, args.user, password)).database_exists():
        print(f"La base '{args.database}' ya existe: use una base nueva para no modificar datos reales")
        return 2

    settings_path = Path(tempfile.mkdtemp()) / "settings.json"
    st.settings_file = lambda: settings_path

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QMessageBox

    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    for name in ("information", "warning", "critical"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: print("  [aviso]", a[1:3])))

    from ladm_admin.core.ili2db import ImportMode
    from ladm_admin.ui import theme
    from ladm_admin.ui.context import AppContext
    from ladm_admin.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    settings = st.load_settings(settings_path)
    conn = st.ConnectionProfile("Local", args.host, args.port, args.database, args.user, save_password=False)
    settings.upsert_connection(conn)
    settings.active_connection = conn.name
    st.set_password(conn, password)
    ctx = AppContext(settings)
    theme.apply(app, "claro")
    win = MainWindow(ctx)
    win.resize(1360, 880)
    win.show()
    out: Path = args.salida
    out.mkdir(parents=True, exist_ok=True)
    ej = {k: str(args.ejemplos / v) for k, v in ARCHIVOS.items()}
    modal_handler: list = []
    steps: list = []

    def poll_modal():
        w = app.activeModalWidget()
        if w is not None and modal_handler:
            handler = modal_handler.pop(0)
            QTimer.singleShot(400, lambda: handler(w))
        QTimer.singleShot(300, poll_modal)

    def shot(name, widget=None):
        (widget or win).grab().save(str(out / f"{name}.png"))
        print("captura", name)

    def wait_idle(then, key, delay=500):
        def check():
            page = win.pages[key]
            busy = ctx.busy or (getattr(page, "job", None) and page.job.is_running()) \
                or getattr(page, "_helper_jobs", [])
            QTimer.singleShot(delay, check) if busy else QTimer.singleShot(400, then)
        QTimer.singleShot(delay, check)

    def nxt():
        if steps:
            steps.pop(0)()
        else:
            app.quit()

    def inicio():
        win.go("home")
        wait_idle(lambda: (shot("01_inicio"), nxt()), "home", 3000)

    def validar():
        win.go("validate")
        p = win.pages["validate"]
        p.add_paths([ej["valido"], ej["otro_modelo"], ej["valido2"]])
        p.start()

        def done():
            shot("02_validar")
            row = next(i for i, s in enumerate(p.sources) if s.path.name == ARCHIVOS["otro_modelo"])

            def grab(w):
                w.resize(1150, 520)
                QTimer.singleShot(300, lambda: (shot("03_validar_errores", w), w.accept(),
                                                QTimer.singleShot(300, nxt)))
            modal_handler.append(grab)
            p._show_issues(row)
        wait_idle(done, "validate")

    def crear():
        win.go("create")
        p = win.pages["create"]
        p.codes.setPlainText(", ".join(Path(ej[k]).stem for k in ("valido", "valido2")))
        p._check_db()

        def run():
            shot("04_crear")
            p.start()
            wait_idle(lambda: (shot("05_crear_resultado"), nxt()), "create")
        wait_idle(run, "create")

    def importar_inicial():
        win.go("import")
        p = win.pages["import"]
        p.add_paths([ej["valido"]])
        wait_idle(lambda: (p.start(), wait_idle(
            lambda: (p._clear(), p.log.clear(), p.results.setRowCount(0), nxt()), "import")), "import")

    def importar_plan():
        p = win.pages["import"]
        p.add_paths([ej["valido"], ej["valido2"], ej["sin_esquema"]])

        def run():
            p.form.parentWidget().parentWidget().parentWidget().verticalScrollBar().setValue(220)
            shot("06_importar_plan")

            def grab(w):
                w.adjustSize()
                for rb, value in w._radios:
                    if value == ImportMode.REPLACE:
                        rb.setChecked(True)
                QTimer.singleShot(300, lambda: (shot("07_importar_conflicto", w), w.accept()))
            modal_handler.append(grab)
            p.start()
            wait_idle(lambda: (shot("08_importar_resultado"), nxt()), "import")
        wait_idle(run, "import")

    def exportar():
        win.go("export")
        p = win.pages["export"]
        p.load_targets()

        def run():
            for r in range(p.table.rowCount()):
                p.table.item(r, 0).setCheckState(Qt.Checked)
            p.output.setText(str(Path(tempfile.mkdtemp()) / "salida"))
            p.start()
            wait_idle(lambda: (shot("09_exportar"), nxt()), "export")
        wait_idle(run, "export")

    def configuracion():
        win.go("settings")
        sp = win.pages["settings"]
        sp.tabs.setCurrentIndex(0)
        QTimer.singleShot(800, lambda: (shot("10_config_conexiones"), sp.tabs.setCurrentIndex(1),
                                        QTimer.singleShot(800, lambda: (shot("11_config_perfiles"), nxt()))))

    steps.extend([inicio, validar, crear, importar_inicial, importar_plan, exportar, configuracion])
    QTimer.singleShot(300, poll_modal)
    QTimer.singleShot(800, nxt)
    app.exec()
    print(f"Listo. Elimine la base de datos '{args.database}' si ya no la necesita.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
