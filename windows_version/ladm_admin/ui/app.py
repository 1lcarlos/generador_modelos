"""Arranque de la interfaz gráfica."""

from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from .. import APP_NAME, APP_ORG, APP_SHORT, __version__
from . import theme
from .context import AppContext
from .icons import icon


def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    sys.__stderr__.write(text)
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(None, "Error inesperado", f"{exc_type.__name__}: {exc}\n\n"
                             "El detalle se escribió en la consola.")


def run(argv: list[str] | None = None) -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_SHORT)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationVersion(__version__)
    app.setFont(QFont("Segoe UI", 10))
    sys.excepthook = _excepthook

    ctx = AppContext()
    theme.apply(app, ctx.settings.ui.get("theme", "sistema"))
    app.setWindowIcon(icon("layers", theme.tokens().primary, 32))

    from .main_window import MainWindow

    window = MainWindow(ctx)
    window.show()
    code = app.exec()
    ctx.save()
    return code


if __name__ == "__main__":
    sys.exit(run())
