"""Estado compartido de la aplicación (configuración, conexión y perfil activos)."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from ..core.database import ConnectionParams
from ..core.ili2db import ToolConfig
from ..core.naming import NamingConvention
from ..core.settings import (
    AppSettings, ConnectionProfile, ModelProfile, get_password, load_settings, save_settings, set_password,
)


class AppContext(QObject):
    settingsChanged = Signal()
    connectionChanged = Signal()
    profileChanged = Signal()
    busyChanged = Signal(bool)
    navigateRequested = Signal(str)

    def __init__(self, settings: AppSettings | None = None):
        super().__init__()
        self.settings = settings or load_settings()
        self._busy = False

    # ------------------------------------------------------------- estado
    @property
    def busy(self) -> bool:
        return self._busy

    def set_busy(self, value: bool) -> None:
        if value != self._busy:
            self._busy = value
            self.busyChanged.emit(value)

    def save(self) -> None:
        save_settings(self.settings)

    def notify_settings(self) -> None:
        self.save()
        self.settingsChanged.emit()

    # ---------------------------------------------------------- selección
    def connection_profile(self) -> ConnectionProfile | None:
        return self.settings.connection()

    def model_profile(self) -> ModelProfile | None:
        return self.settings.model_profile()

    def set_active_connection(self, name: str) -> None:
        if name != self.settings.active_connection:
            self.settings.active_connection = name
            self.save()
            self.connectionChanged.emit()

    def set_active_profile(self, name: str) -> None:
        if name != self.settings.active_model_profile:
            self.settings.active_model_profile = name
            self.save()
            self.profileChanged.emit()

    def tools(self) -> ToolConfig:
        return self.settings.tools.resolve()

    def naming(self) -> NamingConvention:
        return NamingConvention(self.settings.schema_prefix)

    def connection_params(self, parent: QWidget | None = None, ask: bool = True) -> ConnectionParams | None:
        """Parámetros de la conexión activa; pide la contraseña si no está guardada."""
        prof = self.connection_profile()
        if prof is None:
            return None
        password = get_password(prof)
        if password is None and ask:
            from .dialogs import PasswordDialog

            dlg = PasswordDialog(prof, parent)
            if not dlg.exec():
                return None
            password = dlg.password()
            prof.save_password = dlg.remember()
            set_password(prof, password)
            self.save()
        return prof.params(password or "")
