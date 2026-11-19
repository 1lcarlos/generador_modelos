"""Línea de comandos: usa las mismas conexiones y perfiles que la interfaz gráfica.

Ejemplos:
    python -m ladm_admin herramientas
    python -m ladm_admin validar xtf\\ --perfil SINIC
    python -m ladm_admin crear --conexion local --perfil SINIC --esquemas cun25279,cun25436
    python -m ladm_admin importar xtf\\25279 --conexion local --perfil SINIC --si-hay-datos reemplazar
    python -m ladm_admin exportar --conexion local --perfil SINIC --todos --salida salida\\
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from . import APP_NAME, __version__
from .core.database import ConnectionParams
from .core.events import CancelToken, ConsoleReporter, ItemStatus
from .core.ili2db import ImportMode
from .core.naming import NamingConvention, StorageMode
from .core.operations import (
    CreateRequest, ExistingSchemaAction, ExportRequest, ExportTarget, ImportRequest, ValidateRequest,
    analyze_import, check_create_request, list_export_targets, run_create, run_export, run_import,
    run_validation,
)
from .core.database import Database
from .core.settings import AppSettings, get_password, load_settings
from .core.xtf import expand_sources


def _fail(msg: str) -> int:
    print(f"[ERROR] {msg}", file=sys.stderr)
    return 2


def _connection(settings: AppSettings, name: str | None) -> ConnectionParams:
    prof = settings.connection(name)
    if prof is None:
        raise SystemExit(_fail(f"No existe la conexión '{name or '(activa)'}'. "
                               f"Disponibles: {', '.join(c.name for c in settings.connections) or 'ninguna'}"))
    password = os.environ.get("LADM_PGPASSWORD") or get_password(prof)
    if password is None:
        password = getpass.getpass(f"Contraseña para {prof.secret_key}: ")
    return prof.params(password)


def _profile(settings: AppSettings, name: str | None):
    prof = settings.model_profile(name)
    if prof is None:
        raise SystemExit(_fail(f"No existe el perfil de modelo '{name or '(activo)'}'. "
                               f"Disponibles: {', '.join(m.name for m in settings.model_profiles) or 'ninguno'}"))
    return prof


def _exit_code(results) -> int:
    return 1 if any(r.status in (ItemStatus.ERROR, ItemStatus.CANCELLED) for r in results) else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ladm_admin", description=f"{APP_NAME} {__version__}")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("listar", help="Lista conexiones y perfiles de modelo guardados")
    sub.add_parser("herramientas", help="Descarga e instala ili2pg e ilivalidator si faltan")

    v = sub.add_parser("validar", help="Valida archivos XTF con ilivalidator")
    v.add_argument("rutas", nargs="+", help="Archivos .xtf/.zip o carpetas")
    v.add_argument("--perfil", help="Perfil de modelo (para la carpeta de modelos)")
    v.add_argument("--modeldir", help="Carpeta de modelos (anula la del perfil)")
    v.add_argument("--modelos", help="Modelos separados por ';' (por defecto los de la cabecera)")
    v.add_argument("--todos-accesibles", action="store_true", help="--allObjectsAccessible")

    c = sub.add_parser("crear", help="Crea esquemas con ili2pg --schemaimport")
    c.add_argument("--conexion")
    c.add_argument("--perfil")
    c.add_argument("--esquemas", required=True, help="Lista separada por comas")
    c.add_argument("--si-existe", choices=["recrear", "actualizar", "omitir"], default="omitir")

    i = sub.add_parser("importar", help="Importa XTF a esquemas existentes")
    i.add_argument("rutas", nargs="+")
    i.add_argument("--conexion")
    i.add_argument("--perfil")
    i.add_argument("--esquema-unico", help="Importar todo a este esquema (un dataset por municipio)")
    i.add_argument("--si-hay-datos", choices=["reemplazar", "agregar", "cancelar"], default="cancelar")
    i.add_argument("--sin-validacion", action="store_true")
    i.add_argument("--solo-analizar", action="store_true", help="Muestra el plan sin importar")

    e = sub.add_parser("exportar", help="Exporta esquemas o datasets a XTF")
    e.add_argument("--conexion")
    e.add_argument("--perfil")
    e.add_argument("--salida", required=True)
    g = e.add_mutually_exclusive_group()
    g.add_argument("--esquemas", help="Lista separada por comas")
    g.add_argument("--todos", action="store_true", help="Todos los esquemas con el prefijo configurado")
    e.add_argument("--esquema-unico", help="Exportar los datasets de este esquema")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    tools = settings.tools.resolve()
    rep = ConsoleReporter(verbose=False)
    cancel = CancelToken()
    naming = NamingConvention(settings.schema_prefix)

    if args.cmd == "herramientas":
        from .core.tools_setup import ToolSetupError, install_missing
        try:
            install_missing()
        except ToolSetupError as exc:
            return _fail(str(exc))
        return 0

    if args.cmd in (None, "listar"):
        print("Conexiones:")
        for c in settings.connections:
            print(f"  {'*' if c.name == settings.active_connection else ' '} {c.name}: {c.secret_key}")
        print("Perfiles de modelo:")
        for m in settings.model_profiles:
            print(f"  {'*' if m.name == settings.active_model_profile else ' '} {m.name}: {', '.join(m.models)}")
        return 0

    try:
        if args.cmd == "validar":
            modeldir = args.modeldir or (_profile(settings, args.perfil).modeldir if args.perfil else "")
            files, errors = expand_sources(args.rutas)
            for err in errors:
                print(f"[AVISO] {err}")
            if not files:
                return _fail("No se encontraron archivos .xtf")
            res = run_validation(ValidateRequest(tools, files, modeldir=modeldir,
                                                 models=[m for m in (args.modelos or "").split(";") if m],
                                                 all_objects_accessible=args.todos_accesibles), rep, cancel)
            return _exit_code(res)

        if args.cmd == "crear":
            schemas = [s.strip() for s in args.esquemas.split(",") if s.strip()]
            req = CreateRequest(_connection(settings, args.conexion), tools, _profile(settings, args.perfil),
                                schemas, settings.effective_log_dir(),
                                on_existing=ExistingSchemaAction(args.si_existe))
            problems = check_create_request(req)
            if problems:
                return _fail("; ".join(problems))
            return _exit_code(run_create(req, rep, cancel))

        if args.cmd == "importar":
            files, errors = expand_sources(args.rutas)
            for err in errors:
                print(f"[AVISO] {err}")
            req = ImportRequest(
                _connection(settings, args.conexion), tools, _profile(settings, args.perfil).modeldir,
                settings.effective_log_dir(), naming=naming,
                storage_mode=StorageMode.SHARED if args.esquema_unico else StorageMode.PER_MUNICIPALITY,
                shared_schema=args.esquema_unico or "", conflict_mode=ImportMode(args.si_hay_datos),
                disable_validation=args.sin_validacion,
            )
            items = analyze_import(req, files, rep, cancel, scan_objects=True)
            for it in items:
                print(f"  {it.source.display:40} -> {it.schema or '?':15} {it.dataset or '':10} {it.state.label}"
                      + (f"  ({'; '.join(it.messages)})" if it.messages else ""))
            if args.solo_analizar:
                return 0
            return _exit_code(run_import(req, items, rep, cancel))

        if args.cmd == "exportar":
            conn = _connection(settings, args.conexion)
            if args.esquema_unico:
                targets = list_export_targets(Database(conn), StorageMode.SHARED, naming, args.esquema_unico)
            elif args.todos:
                targets = list_export_targets(Database(conn), StorageMode.PER_MUNICIPALITY, naming)
            elif args.esquemas:
                targets = [ExportTarget(s.strip(), naming.code_for_schema(s.strip()))
                           for s in args.esquemas.split(",") if s.strip()]
            else:
                return _fail("Indique --esquemas, --todos o --esquema-unico")
            req = ExportRequest(conn, tools, _profile(settings, args.perfil).modeldir, Path(args.salida), targets)
            return _exit_code(run_export(req, rep, cancel))
    except KeyboardInterrupt:
        cancel.cancel()
        print("\nInterrumpido por el usuario")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
