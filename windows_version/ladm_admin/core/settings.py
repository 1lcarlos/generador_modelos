"""Configuración persistente: conexiones, perfiles de modelo y herramientas.

Se guarda en %APPDATA%\\LADMAdmin\\settings.json. Las contraseñas NO se guardan
en ese archivo: van al Administrador de credenciales de Windows (keyring).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths
from .database import ConnectionParams
from .ili2db import ToolConfig, default_schema_options

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # pragma: no cover
    keyring = None
    KeyringError = Exception

KEYRING_SERVICE = "LADMAdmin"
SETTINGS_VERSION = 1


@dataclass
class ConnectionProfile:
    name: str
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = "postgres"
    save_password: bool = True

    @property
    def secret_key(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.database}"

    def params(self, password: str | None = None) -> ConnectionParams:
        pwd = password if password is not None else (get_password(self) or "")
        return ConnectionParams(self.host, int(self.port), self.database, self.user, pwd)


@dataclass
class ModelProfile:
    """Conjunto de modelos + opciones de ili2pg (ej. 'SINIC v1.0', 'Interno ACC V3')."""

    name: str
    modeldir: str = ""
    models: list[str] = field(default_factory=list)
    srs_code: str = "9377"
    options: dict[str, bool] = field(default_factory=default_schema_options)
    prescript: str = ""

    def normalized_options(self) -> dict[str, bool]:
        opts = default_schema_options()
        opts.update({k: bool(v) for k, v in self.options.items() if k in opts})
        return opts


@dataclass
class ToolSettings:
    java: str = ""
    ili2pg_jar: str = ""
    ilivalidator_jar: str = ""
    java_max_memory: str = ""

    def resolve(self) -> ToolConfig:
        java = paths.find_java(self.java) or "java"
        return ToolConfig(
            java=java,
            ili2pg_jar=self.ili2pg_jar or str(paths.default_ili2pg_jar()),
            ilivalidator_jar=self.ilivalidator_jar or str(paths.default_ilivalidator_jar()),
            java_max_memory=self.java_max_memory,
        )


@dataclass
class AppSettings:
    tools: ToolSettings = field(default_factory=ToolSettings)
    log_dir: str = ""
    schema_prefix: str = "cun"
    connections: list[ConnectionProfile] = field(default_factory=list)
    model_profiles: list[ModelProfile] = field(default_factory=list)
    active_connection: str = ""
    active_model_profile: str = ""
    ui: dict = field(default_factory=dict)   # estado libre de la interfaz (rutas recientes, etc.)
    version: int = SETTINGS_VERSION

    # ------------------------------------------------------------- busquedas
    def connection(self, name: str | None = None) -> ConnectionProfile | None:
        name = name or self.active_connection
        return next((c for c in self.connections if c.name == name), None)

    def model_profile(self, name: str | None = None) -> ModelProfile | None:
        name = name or self.active_model_profile
        return next((m for m in self.model_profiles if m.name == name), None)

    def effective_log_dir(self) -> Path:
        path = Path(self.log_dir) if self.log_dir else paths.default_log_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upsert_connection(self, profile: ConnectionProfile, old_name: str | None = None) -> None:
        key = old_name or profile.name
        self.connections = [c for c in self.connections if c.name not in (key, profile.name)]
        self.connections.append(profile)
        self.connections.sort(key=lambda c: c.name.lower())

    def upsert_model_profile(self, profile: ModelProfile, old_name: str | None = None) -> None:
        key = old_name or profile.name
        self.model_profiles = [m for m in self.model_profiles if m.name not in (key, profile.name)]
        self.model_profiles.append(profile)
        self.model_profiles.sort(key=lambda m: m.name.lower())


# ---------------------------------------------------------------- contraseñas
_session_passwords: dict[str, str] = {}


def keyring_available() -> bool:
    if keyring is None:
        return False
    try:
        backend = keyring.get_keyring()
        return "fail" not in type(backend).__module__.lower()
    except Exception:  # pragma: no cover
        return False


def get_password(profile: ConnectionProfile) -> str | None:
    if profile.secret_key in _session_passwords:
        return _session_passwords[profile.secret_key]
    if profile.save_password and keyring_available():
        try:
            return keyring.get_password(KEYRING_SERVICE, profile.secret_key)
        except KeyringError:
            return None
    return None


def set_password(profile: ConnectionProfile, password: str) -> bool:
    """Guarda la contraseña. Devuelve True si quedo persistida en el keyring."""
    _session_passwords[profile.secret_key] = password
    if profile.save_password and keyring_available():
        try:
            keyring.set_password(KEYRING_SERVICE, profile.secret_key, password)
            return True
        except KeyringError:
            return False
    return False


def delete_password(profile: ConnectionProfile) -> None:
    _session_passwords.pop(profile.secret_key, None)
    if keyring_available():
        try:
            keyring.delete_password(KEYRING_SERVICE, profile.secret_key)
        except Exception:
            pass


# ------------------------------------------------------------- persistencia
def settings_file() -> Path:
    return paths.config_dir() / "settings.json"


def _from_dict(data: dict) -> AppSettings:
    s = AppSettings()
    s.tools = ToolSettings(**{k: v for k, v in data.get("tools", {}).items() if k in ToolSettings.__dataclass_fields__})
    s.log_dir = data.get("log_dir", "")
    s.schema_prefix = data.get("schema_prefix", "cun")
    s.connections = [
        ConnectionProfile(**{k: v for k, v in c.items() if k in ConnectionProfile.__dataclass_fields__})
        for c in data.get("connections", [])
    ]
    s.model_profiles = [
        ModelProfile(**{k: v for k, v in m.items() if k in ModelProfile.__dataclass_fields__})
        for m in data.get("model_profiles", [])
    ]
    s.active_connection = data.get("active_connection", "")
    s.active_model_profile = data.get("active_model_profile", "")
    s.ui = data.get("ui", {}) or {}
    return s


def load_settings(path: Path | None = None) -> AppSettings:
    path = path or settings_file()
    if not path.exists():
        settings = AppSettings()
        _add_bundled_defaults(settings)
        return settings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        backup = path.with_suffix(".json.corrupto")
        try:
            path.replace(backup)
        except OSError:
            pass
        settings = AppSettings()
        _add_bundled_defaults(settings)
        return settings
    return _from_dict(data)


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    path = path or settings_file()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _add_bundled_defaults(settings: AppSettings) -> None:
    """Primer arranque: crea un perfil para cada carpeta de Modelos/ incluida."""
    from .ili import scan_model_dir, suggested_models

    models_root = paths.base_dir() / "Modelos"
    if not models_root.is_dir():
        return
    for folder in sorted(p for p in models_root.iterdir() if p.is_dir()):
        models = scan_model_dir(folder)
        if not models:
            continue
        ctm12 = paths.default_ctm12_script()
        settings.upsert_model_profile(
            ModelProfile(
                name=folder.name,
                modeldir=str(folder),
                models=suggested_models(models),
                prescript=str(ctm12) if ctm12.exists() else "",
            )
        )
    if settings.model_profiles and not settings.active_model_profile:
        settings.active_model_profile = settings.model_profiles[0].name


# ------------------------------------------------------- migracion (v2.0)
LEGACY_DIR = Path.home() / ".ili2pg_gui"


def legacy_profiles_available() -> bool:
    return (LEGACY_DIR / "profiles.json").exists() or (LEGACY_DIR / "last_profile.json").exists()


def import_legacy_profiles(settings: AppSettings) -> tuple[int, int]:
    """Importa perfiles de la version 2.0 (Tkinter). Devuelve (conexiones, perfiles de modelo).

    Las contraseñas que estaban en texto plano se trasladan al keyring.
    """
    from .ili import parse_ili_file

    sources: dict[str, dict] = {}
    try:
        sources.update(json.loads((LEGACY_DIR / "profiles.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass
    try:
        sources.setdefault("Última sesión", json.loads((LEGACY_DIR / "last_profile.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass

    n_conn = n_models = 0
    known_conn = {c.secret_key for c in settings.connections}
    known_models = {(m.modeldir, tuple(m.models)) for m in settings.model_profiles}

    def add_conn(name: str, host, port, db, user, pwd) -> None:
        nonlocal n_conn
        if not db:
            return
        prof = ConnectionProfile(name=name, host=host or "localhost", port=int(port or 5432),
                                 database=db, user=user or "postgres")
        if prof.secret_key in known_conn:
            return
        existing = {c.name for c in settings.connections}
        base, i = prof.name, 2
        while prof.name in existing:
            prof.name = f"{base} ({i})"
            i += 1
        settings.upsert_connection(prof)
        if pwd:
            set_password(prof, pwd)
        known_conn.add(prof.secret_key)
        n_conn += 1

    for name, cfg in sources.items():
        add_conn(f"{cfg.get('db_name') or name}", cfg.get("db_host"), cfg.get("db_port"),
                 cfg.get("db_name"), cfg.get("db_user"), cfg.get("db_password"))
        exp = cfg.get("export") or {}
        add_conn(f"{exp.get('db_name') or name}", exp.get("db_host"), exp.get("db_port"),
                 exp.get("db_name"), exp.get("db_user"), exp.get("db_password"))

        folder = cfg.get("models_folder") or ""
        files = cfg.get("selected_models") or []
        model_names: list[str] = []
        for f in files:
            fp = Path(folder) / f
            try:
                model_names.extend(m.name for m in parse_ili_file(fp))
            except OSError:
                model_names.append(re.sub(r"\.ili$", "", f, flags=re.I))
        if folder and model_names and (folder, tuple(model_names)) not in known_models:
            existing = {m.name for m in settings.model_profiles}
            pname = Path(folder).name or name
            base, i = pname, 2
            while pname in existing:
                pname = f"{base} ({i})"
                i += 1
            opts = default_schema_options()
            opts.update({k: bool(v) for k, v in (cfg.get("options") or {}).items() if k in opts})
            settings.upsert_model_profile(ModelProfile(
                name=pname, modeldir=folder, models=model_names,
                srs_code=str(cfg.get("srs_code") or "9377"), options=opts,
                prescript=cfg.get("ctm12_path") or "",
            ))
            known_models.add((folder, tuple(model_names)))
            n_models += 1
    return n_conn, n_models
