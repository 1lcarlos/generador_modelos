"""Operaciones de la herramienta: validar, crear esquemas, importar y exportar.

Flujo recomendado:  validar XTF -> crear esquema -> importar -> exportar.

Cada operación recibe una solicitud (dataclass), un ``Reporter`` y un
``CancelToken``; devuelve una lista de ``ItemResult``. No depende de la GUI.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable

from .database import ConnectionParams, Database, DatabaseError, SchemaInfo
from .events import Cancelled, CancelToken, ItemStatus, Level, Reporter
from .ili2db import Ili2pg, Ilivalidator, ImportMode, ToolConfig, ensure_parent
from .naming import NamingConvention, StorageMode, code_from_path, validate_identifier
from .process import ToolResult, run_tool
from .settings import ModelProfile
from .xtf import SourceFile, XtfInfo, read_header, scan_content


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass
class ItemResult:
    key: str
    status: ItemStatus
    detail: str = ""
    log_file: str = ""
    output_file: str = ""
    duration: float = 0.0
    errors: int = 0
    warnings: int = 0
    extra: dict = field(default_factory=dict)


def _status_from_tool(result: ToolResult) -> ItemStatus:
    if result.cancelled:
        return ItemStatus.CANCELLED
    if result.returncode != 0:
        return ItemStatus.ERROR
    return ItemStatus.WARNING if result.warnings else ItemStatus.OK


def _header(reporter: Reporter, title: str) -> None:
    reporter.log(title, Level.HEADER)


def _summary(reporter: Reporter, results: list[ItemResult]) -> None:
    counts = Counter(r.status for r in results)
    parts = [f"{counts[s]} {s.label.lower()}" for s in ItemStatus if counts[s]]
    level = Level.ERROR if counts[ItemStatus.ERROR] else (Level.WARNING if counts[ItemStatus.WARNING] else Level.SUCCESS)
    reporter.log("Resumen: " + (", ".join(parts) if parts else "sin elementos procesados"), level)


# =============================================================== VALIDAR XTF
@dataclass
class ValidateRequest:
    tools: ToolConfig
    files: list[SourceFile]
    modeldir: str = ""
    models: list[str] = field(default_factory=list)   # vacío = los de la cabecera del XTF
    xtflog: bool = False
    csvlog: bool = True
    all_objects_accessible: bool = False
    config_file: str = ""


def _report_base(src: SourceFile) -> Path:
    """Los reportes se guardan junto al XTF; si viene de un ZIP, junto al ZIP."""
    if src.origin is not None:
        return src.origin.parent / f"{src.origin.stem}_{src.path.stem}"
    return src.path.parent / src.path.stem


def run_validation(req: ValidateRequest, reporter: Reporter, cancel: CancelToken) -> list[ItemResult]:
    _header(reporter, f"Validación de {len(req.files)} archivo(s) XTF")
    validator = Ilivalidator(req.tools, modeldir=req.modeldir)
    results: list[ItemResult] = []
    total = len(req.files)
    for i, src in enumerate(req.files, 1):
        key = str(src.path)
        if cancel.cancelled:
            reporter.item(key, ItemStatus.CANCELLED)
            results.append(ItemResult(key, ItemStatus.CANCELLED))
            continue
        reporter.progress(i - 1, total, f"Validando {src.display}")
        reporter.item(key, ItemStatus.RUNNING)
        reporter.log(f"[{i}/{total}] {src.display}", Level.INFO)
        base = _report_base(src)
        log_file = f"{base}_validacion.log"
        cmd = validator.validate(
            str(src.path),
            models=req.models or None,
            log_file=log_file,
            xtflog=f"{base}_validacion.xtf" if req.xtflog else "",
            csvlog=f"{base}_validacion.csv" if req.csvlog else "",
            config_file=req.config_file,
            all_objects_accessible=req.all_objects_accessible,
        )
        res = run_tool(cmd, reporter, cancel)
        status = _status_from_tool(res)
        if status == ItemStatus.ERROR:
            detail = f"{len(res.errors)} error(es) de validación" if res.errors else res.summary()
        elif status == ItemStatus.CANCELLED:
            detail = "Cancelado"
        else:
            detail = "Válido" + (f" con {len(res.warnings)} advertencia(s)" if res.warnings else "")
        item = ItemResult(key, status, detail, log_file=log_file, duration=res.duration,
                          errors=len(res.errors), warnings=len(res.warnings),
                          extra={"csv": f"{base}_validacion.csv" if req.csvlog else ""})
        results.append(item)
        reporter.item(key, status, detail, errors=item.errors, warnings=item.warnings,
                      log_file=log_file, duration=res.duration)
        reporter.log(f"{src.display}: {detail}", Level.SUCCESS if status in (ItemStatus.OK, ItemStatus.WARNING) else Level.ERROR)
    reporter.progress(total, total, "Validación finalizada")
    _summary(reporter, results)
    return results


# ============================================================= CREAR ESQUEMA
class ExistingSchemaAction(str, Enum):
    RECREATE = "recrear"
    UPDATE = "actualizar"
    SKIP = "omitir"
    ASK = "preguntar"
    ABORT = "abortar"

    @property
    def label(self) -> str:
        return {
            ExistingSchemaAction.RECREATE: "Recrear (borra el esquema y sus datos)",
            ExistingSchemaAction.UPDATE: "Actualizar estructura (conserva datos)",
            ExistingSchemaAction.SKIP: "Omitir",
            ExistingSchemaAction.ASK: "Preguntar en cada caso",
            ExistingSchemaAction.ABORT: "Detener el proceso",
        }[self]


SchemaDecider = Callable[[SchemaInfo], tuple[ExistingSchemaAction, bool]]


@dataclass
class CreateRequest:
    conn: ConnectionParams
    tools: ToolConfig
    profile: ModelProfile
    schemas: list[str]
    log_dir: Path
    on_existing: ExistingSchemaAction = ExistingSchemaAction.ASK
    create_database: bool = True
    storage_mode: StorageMode = StorageMode.PER_MUNICIPALITY


def check_create_request(req: CreateRequest) -> list[str]:
    errors = []
    if not req.schemas:
        errors.append("No hay esquemas para crear")
    for s in req.schemas:
        msg = validate_identifier(s)
        if msg:
            errors.append(f"Esquema '{s}': {msg}")
    if not req.profile.models:
        errors.append("El perfil de modelo no tiene modelos seleccionados")
    opts = req.profile.normalized_options()
    if req.storage_mode == StorageMode.SHARED and not opts.get("createBasketCol"):
        errors.append("El esquema único con datasets requiere la opción 'Columna de basket' (createBasketCol)")
    if not Path(req.tools.ili2pg_jar).is_file():
        errors.append(f"No existe ili2pg: {req.tools.ili2pg_jar}")
    if req.profile.prescript and not Path(req.profile.prescript).is_file():
        errors.append(f"No existe el script previo (CTM12): {req.profile.prescript}")
    return errors


def run_create(req: CreateRequest, reporter: Reporter, cancel: CancelToken,
               decide: SchemaDecider | None = None) -> list[ItemResult]:
    _header(reporter, f"Creación de {len(req.schemas)} esquema(s) - perfil '{req.profile.name}'")
    db = Database(req.conn)
    results: list[ItemResult] = []
    try:
        if not db.database_exists():
            if not req.create_database:
                raise DatabaseError(f"La base de datos '{req.conn.database}' no existe")
            reporter.log(f"Creando base de datos '{req.conn.database}'...", Level.INFO)
            db.create_database()
        db.ensure_extensions()
        reporter.log("Extensiones postgis y uuid-ossp disponibles", Level.DEBUG)
    except DatabaseError as exc:
        reporter.log(f"Error de base de datos: {exc}", Level.ERROR)
        for s in req.schemas:
            reporter.item(s, ItemStatus.ERROR, str(exc))
            results.append(ItemResult(s, ItemStatus.ERROR, str(exc)))
        return results

    ili2pg = Ili2pg(req.tools, req.conn, modeldir=req.profile.modeldir)
    remembered: ExistingSchemaAction | None = None
    total = len(req.schemas)
    log_dir = req.log_dir / "crear_esquema"
    try:
        for i, schema in enumerate(req.schemas, 1):
            cancel.raise_if_cancelled()
            reporter.progress(i - 1, total, f"Creando {schema}")
            reporter.item(schema, ItemStatus.RUNNING)
            reporter.log(f"[{i}/{total}] Esquema {schema}", Level.INFO)
            info = db.inspect_schema(schema)
            action = None
            if info.exists:
                action = remembered or req.on_existing
                if action == ExistingSchemaAction.ASK:
                    if decide is None:
                        action = ExistingSchemaAction.SKIP
                    else:
                        action, apply_all = decide(info)
                        if apply_all:
                            remembered = action
                if action == ExistingSchemaAction.ABORT:
                    raise Cancelled()
                if action == ExistingSchemaAction.SKIP:
                    results.append(ItemResult(schema, ItemStatus.SKIPPED, "El esquema ya existe"))
                    reporter.item(schema, ItemStatus.SKIPPED, "El esquema ya existe")
                    continue
            backup = None
            if action == ExistingSchemaAction.RECREATE:
                # Se renombra en lugar de borrar: si la creación falla se restaura.
                backup = f"{schema[:40]}__respaldo_{_stamp()}"
                reporter.log(f"Respaldando esquema existente como '{backup}'", Level.WARNING)
                db.rename_schema(schema, backup)

            log_file = ensure_parent(log_dir / f"{_stamp()}_{schema}.log")
            cmd = ili2pg.schema_import(
                schema, req.profile.models, req.profile.srs_code, req.profile.normalized_options(),
                prescript=req.profile.prescript, log_file=log_file,
            )
            res = ToolResult(returncode=None, cancelled=True)
            try:
                res = run_tool(cmd, reporter, cancel)
            finally:
                if backup:
                    if res.ok:
                        db.drop_schema(backup)
                        reporter.log(f"Esquema anterior eliminado ('{backup}')", Level.DEBUG)
                    else:
                        db.drop_schema(schema)
                        db.rename_schema(backup, schema)
                        reporter.log(f"La creación falló: se restauró el esquema original '{schema}'", Level.WARNING)
            status = _status_from_tool(res)
            detail = res.summary()
            if res.ok:
                after = db.inspect_schema(schema)
                detail = (f"{'Actualizado' if action == ExistingSchemaAction.UPDATE else 'Creado'}: "
                          f"{after.table_count} tablas, {len(after.models)} modelo(s)"
                          + (", con soporte de datasets" if after.basket_col else ""))
            results.append(ItemResult(schema, status, detail, log_file=log_file, duration=res.duration,
                                      errors=len(res.errors), warnings=len(res.warnings)))
            reporter.item(schema, status, detail, log_file=log_file, duration=res.duration)
            reporter.log(f"{schema}: {detail}", Level.SUCCESS if res.ok else Level.ERROR)
    except Cancelled:
        reporter.log("Proceso detenido por el usuario", Level.WARNING)
        done = {r.key for r in results}
        for s in req.schemas:
            if s not in done:
                results.append(ItemResult(s, ItemStatus.CANCELLED))
                reporter.item(s, ItemStatus.CANCELLED)
    except DatabaseError as exc:
        reporter.log(f"Error de base de datos: {exc}", Level.ERROR)
    reporter.progress(total, total, "Creación finalizada")
    _summary(reporter, results)
    return results


# ================================================================== IMPORTAR
class PlanState(str, Enum):
    READY = "listo"          # se puede importar sin conflicto
    CONFLICT = "conflicto"   # el destino ya tiene datos: aplica la politica elegida
    BLOCKED = "bloqueado"    # no se puede importar (ver mensajes)

    @property
    def label(self) -> str:
        return {PlanState.READY: "Listo", PlanState.CONFLICT: "Ya tiene datos",
                PlanState.BLOCKED: "Bloqueado"}[self]


@dataclass
class ImportItem:
    source: SourceFile
    header: XtfInfo
    code: str | None = None
    schema: str = ""
    dataset: str | None = None
    state: PlanState = PlanState.BLOCKED
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_info: SchemaInfo | None = None
    enabled: bool = True

    @property
    def key(self) -> str:
        return str(self.source.path)


@dataclass
class ImportRequest:
    conn: ConnectionParams
    tools: ToolConfig
    modeldir: str
    log_dir: Path
    storage_mode: StorageMode = StorageMode.PER_MUNICIPALITY
    naming: NamingConvention = field(default_factory=NamingConvention)
    shared_schema: str = ""
    conflict_mode: ImportMode = ImportMode.ASK
    disable_validation: bool = False
    skip_reference_errors: bool = False
    skip_geometry_errors: bool = False
    verify_counts: bool = True


ConflictDecider = Callable[[ImportItem], tuple[ImportMode, bool]]


def _target_for(item: ImportItem, req: ImportRequest) -> None:
    if req.storage_mode == StorageMode.SHARED:
        item.schema = req.shared_schema
    elif item.code and not item.schema:
        item.schema = req.naming.schema_for_code(item.code)


def evaluate_item(item: ImportItem, req: ImportRequest, info: SchemaInfo | None,
                  claimed: set[tuple[str, str | None]], class_map: dict[str, str] | None = None) -> None:
    """Determina si un elemento del plan esta listo, en conflicto o bloqueado."""
    item.messages.clear()
    item.warnings.clear()
    item.schema_info = info
    if item.header.error:
        item.messages.append(item.header.error)
    if not item.schema:
        item.messages.append("No se detectó el código de municipio: indique el esquema destino")
    elif info is None or not info.exists:
        item.messages.append(f"El esquema '{item.schema}' no existe. Créelo primero en 'Crear esquema'")
    elif not info.is_ili2db:
        item.messages.append(f"El esquema '{item.schema}' no fue creado con ili2db")
    if item.messages or info is None:
        item.state = PlanState.BLOCKED
        return

    missing = [m for m in item.header.model_names if m not in info.models]
    if missing:
        item.messages.append("Modelos del XTF que no están en el esquema: " + ", ".join(missing))
    version = info.ili2db_version
    if version and not version.startswith("5."):
        item.warnings.append(f"Esquema creado con ili2pg {version}; se recomienda recrearlo con la versión 5.5.1")
    if req.storage_mode == StorageMode.SHARED and not info.basket_col:
        item.messages.append("El esquema único requiere haber sido creado con 'Columna de basket'")
    if class_map is not None and item.header.class_counts:
        no_table = sorted(c for c in item.header.class_counts if c not in class_map)
        if no_table:
            item.messages.append(
                f"{len(no_table)} clase(s) del XTF sin tabla en el esquema (¿se creo sin todos los modelos?): "
                + ", ".join(no_table[:5]) + (" ..." if len(no_table) > 5 else ""))
    if item.messages:
        item.state = PlanState.BLOCKED
        return

    if info.basket_col:
        item.dataset = item.dataset or item.code or Path(item.source.path).stem
    else:
        item.dataset = None
        item.warnings.append("Esquema sin 'Columna de basket': no se podrá reemplazar por dataset")

    target = (item.schema, item.dataset)
    if target in claimed:
        item.messages.append("Otro archivo del lote ya importa a este mismo esquema/dataset")
        item.state = PlanState.BLOCKED
        return
    claimed.add(target)

    if req.storage_mode == StorageMode.SHARED:
        conflict = item.dataset in info.datasets
    else:
        conflict = info.has_data
    item.state = PlanState.CONFLICT if conflict else PlanState.READY


def analyze_import(req: ImportRequest, sources: list[SourceFile], reporter: Reporter,
                   cancel: CancelToken | None = None, scan_objects: bool = False) -> list[ImportItem]:
    """Lee cabeceras, resuelve destinos e inspecciona la base de datos (sin escribir)."""
    items: list[ImportItem] = []
    for src in sources:
        if cancel is not None and cancel.cancelled:
            break
        header = scan_content(src.path) if scan_objects else read_header(src.path)
        item = ImportItem(source=src, header=header, code=code_from_path(src.path, src.origin))
        _target_for(item, req)
        items.append(item)
    reevaluate_import(req, items, reporter)
    return items


def reevaluate_import(req: ImportRequest, items: list[ImportItem], reporter: Reporter) -> None:
    """Vuelve a evaluar el plan (p.ej. después de que el usuario edita destinos)."""
    db = Database(req.conn)
    cache: dict[str, SchemaInfo | None] = {}
    class_maps: dict[str, dict[str, str] | None] = {}
    claimed: set[tuple[str, str | None]] = set()
    for item in items:
        if not item.enabled:
            continue
        info = None
        if item.schema:
            if item.schema not in cache:
                try:
                    cache[item.schema] = db.inspect_schema(item.schema)
                except DatabaseError as exc:
                    reporter.log(f"No se pudo inspeccionar '{item.schema}': {exc}", Level.ERROR)
                    cache[item.schema] = None
            info = cache[item.schema]
            if item.header.class_counts and info is not None and info.is_ili2db:
                if item.schema not in class_maps:
                    try:
                        class_maps[item.schema] = db.class_table_map(item.schema)
                    except DatabaseError:
                        class_maps[item.schema] = None
        evaluate_item(item, req, info, claimed, class_maps.get(item.schema))


def _unique_dataset(base: str, existing: list[str]) -> str:
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def _verify(db: Database, item: ImportItem, dataset: str | None, reporter: Reporter) -> list[str]:
    """Compara objetos por clase del XTF con registros por tabla en la BD."""
    header = item.header if item.header.class_counts else scan_content(item.source.path, item.header)
    if not header.class_counts:
        return []
    mapping = db.class_table_map(item.schema)
    expected: Counter = Counter()
    unmapped = []
    for cls, n in header.class_counts.items():
        table = mapping.get(cls)
        if table:
            expected[table] += n
        else:
            unmapped.append(cls)
    actual = db.count_rows(item.schema, list(expected), dataset=dataset)
    issues = []
    for table, n in sorted(expected.items()):
        got = actual.get(table)
        if got is not None and got != n:
            issues.append(f"{table}: XTF={n}, BD={got}")
    reporter.log(
        f"Verificacion: {header.total_objects} objetos en {len(header.class_counts)} clases; "
        + ("conteos coinciden" if not issues else f"{len(issues)} diferencia(s)"),
        Level.SUCCESS if not issues else Level.WARNING,
    )
    for msg in issues:
        reporter.log(f"  {msg}", Level.WARNING)
    if unmapped:
        reporter.log(f"  Clases sin tabla asociada: {', '.join(unmapped)}", Level.DEBUG)
    return issues


def run_import(req: ImportRequest, items: list[ImportItem], reporter: Reporter, cancel: CancelToken,
               decide: ConflictDecider | None = None) -> list[ItemResult]:
    todo = [it for it in items if it.enabled]
    _header(reporter, f"Importación de {len(todo)} archivo(s) XTF")
    reevaluate_import(req, todo, reporter)
    db = Database(req.conn)
    ili2pg = Ili2pg(req.tools, req.conn, modeldir=req.modeldir)
    results: list[ItemResult] = []
    remembered: ImportMode | None = None
    total = len(todo)
    log_dir = req.log_dir / "importar"

    def finish(item: ImportItem, status: ItemStatus, detail: str, **kw) -> None:
        results.append(ItemResult(item.key, status, detail, **kw))
        reporter.item(item.key, status, detail, **kw)

    try:
        for i, item in enumerate(todo, 1):
            cancel.raise_if_cancelled()
            reporter.progress(i - 1, total, f"Importando {item.source.display}")
            reporter.log(f"[{i}/{total}] {item.source.display} -> {item.schema}"
                         + (f" (dataset {item.dataset})" if item.dataset else ""), Level.INFO)
            for w in item.warnings:
                reporter.log(w, Level.WARNING)
            if item.state == PlanState.BLOCKED:
                detail = "; ".join(item.messages)
                reporter.log(detail, Level.ERROR)
                finish(item, ItemStatus.ERROR, detail)
                continue

            info = item.schema_info
            assert info is not None
            replace = False
            dataset = item.dataset
            if item.state == PlanState.CONFLICT:
                mode = remembered or req.conflict_mode
                if mode == ImportMode.ASK:
                    if decide is None:
                        mode = ImportMode.CANCEL
                    else:
                        mode, apply_all = decide(item)
                        if apply_all:
                            remembered = mode
                if mode is None:
                    raise Cancelled()
                if mode == ImportMode.CANCEL:
                    reporter.log("El destino ya tiene datos: se omite", Level.WARNING)
                    finish(item, ItemStatus.SKIPPED, "El destino ya contiene datos")
                    continue
                if mode == ImportMode.REPLACE:
                    if not info.basket_col:
                        msg = "Reemplazar requiere un esquema creado con 'Columna de basket' (createBasketCol)"
                        reporter.log(msg, Level.ERROR)
                        finish(item, ItemStatus.ERROR, msg)
                        continue
                    replace = True
                    if req.storage_mode == StorageMode.PER_MUNICIPALITY:
                        for other in [d for d in info.datasets if d != dataset]:
                            cancel.raise_if_cancelled()
                            reporter.log(f"Eliminando dataset previo '{other}' de {item.schema}", Level.WARNING)
                            del_log = ensure_parent(log_dir / f"{_stamp()}_{item.schema}_borrar_{other}.log")
                            res = run_tool(ili2pg.delete_dataset(item.schema, other, del_log),
                                           reporter, cancel)
                            if not res.ok:
                                raise RuntimeError(f"No se pudo eliminar el dataset '{other}': {res.summary()}")
                elif mode == ImportMode.APPEND and info.basket_col:
                    dataset = _unique_dataset(dataset or "dataset", info.datasets)
                    reporter.log(f"Se agregará como nuevo dataset '{dataset}'", Level.INFO)

            reporter.item(item.key, ItemStatus.RUNNING)
            log_file = ensure_parent(log_dir / f"{_stamp()}_{item.schema}_{Path(item.source.path).stem}.log")
            cmd = ili2pg.data_import(
                item.schema, str(item.source.path),
                dataset=dataset, replace=replace,
                disable_validation=req.disable_validation,
                skip_reference_errors=req.skip_reference_errors,
                skip_geometry_errors=req.skip_geometry_errors,
                log_file=log_file,
            )
            started = time.monotonic()
            res = run_tool(cmd, reporter, cancel)
            status = _status_from_tool(res)
            detail = res.summary()
            if res.ok:
                detail = ("Datos reemplazados" if replace else "Importado") + (
                    f" en dataset '{dataset}'" if dataset else "")
                if req.verify_counts and (dataset or not info.has_data):
                    try:
                        issues = _verify(db, item, dataset, reporter)
                        if issues:
                            status = ItemStatus.WARNING
                            detail += f"; {len(issues)} diferencia(s) en conteos"
                    except (DatabaseError, OSError) as exc:
                        reporter.log(f"No se pudo verificar conteos: {exc}", Level.WARNING)
            elif res.errors and not res.cancelled:
                detail = f"{len(res.errors)} error(es): {res.main_error()}"
            finish(item, status, detail, log_file=log_file, duration=time.monotonic() - started,
                   errors=len(res.errors), warnings=len(res.warnings))
            reporter.log(f"{item.source.display}: {detail}",
                         Level.SUCCESS if status in (ItemStatus.OK, ItemStatus.WARNING) else Level.ERROR)
            # El estado del esquema cambio: invalidar para los siguientes elementos
            if res.ok:
                reevaluate_import(req, [it for it in todo[i:]], reporter)
    except Cancelled:
        reporter.log("Proceso detenido por el usuario", Level.WARNING)
    except (DatabaseError, RuntimeError) as exc:
        reporter.log(str(exc), Level.ERROR)
    done = {r.key for r in results}
    for item in todo:
        if item.key not in done:
            finish(item, ItemStatus.CANCELLED, "")
    reporter.progress(total, total, "Importación finalizada")
    _summary(reporter, results)
    return results


# ================================================================== EXPORTAR
@dataclass
class ExportTarget:
    schema: str
    code: str
    dataset: str | None = None

    @property
    def key(self) -> str:
        return f"{self.schema}/{self.dataset}" if self.dataset else self.schema


@dataclass
class ExportRequest:
    conn: ConnectionParams
    tools: ToolConfig
    modeldir: str
    output_dir: Path
    targets: list[ExportTarget]
    export_tid: bool = True
    disable_validation: bool = False


def list_export_targets(db: Database, mode: StorageMode, naming: NamingConvention,
                        shared_schema: str = "") -> list[ExportTarget]:
    if mode == StorageMode.SHARED:
        info = db.inspect_schema(shared_schema)
        return [ExportTarget(shared_schema, ds, ds) for ds in info.datasets]
    targets = []
    for schema in db.list_schemas(only_ili2db=True):
        if naming.schema_prefix and not schema.lower().startswith(naming.schema_prefix.lower()):
            continue
        targets.append(ExportTarget(schema, naming.code_for_schema(schema)))
    return targets


def run_export(req: ExportRequest, reporter: Reporter, cancel: CancelToken) -> list[ItemResult]:
    _header(reporter, f"Exportación de {len(req.targets)} destino(s) a XTF")
    db = Database(req.conn)
    ili2pg = Ili2pg(req.tools, req.conn, modeldir=req.modeldir)
    results: list[ItemResult] = []
    total = len(req.targets)
    try:
        for i, tgt in enumerate(req.targets, 1):
            cancel.raise_if_cancelled()
            reporter.progress(i - 1, total, f"Exportando {tgt.key}")
            reporter.item(tgt.key, ItemStatus.RUNNING)
            reporter.log(f"[{i}/{total}] {tgt.key} -> carpeta {tgt.code}", Level.INFO)
            folder = req.output_dir / tgt.code
            folder.mkdir(parents=True, exist_ok=True)
            xtf = folder / f"{tgt.code}.xtf"
            log_file = str(folder / f"{tgt.code}_exportacion.log")
            models = None
            if not tgt.dataset:
                info = db.inspect_schema(tgt.schema)
                if not info.is_ili2db:
                    msg = "El esquema no existe o no fue creado con ili2db"
                    results.append(ItemResult(tgt.key, ItemStatus.ERROR, msg))
                    reporter.item(tgt.key, ItemStatus.ERROR, msg)
                    continue
                models = info.models
            cmd = ili2pg.export(tgt.schema, str(xtf), models=models, dataset=tgt.dataset,
                                export_tid=req.export_tid, disable_validation=req.disable_validation,
                                log_file=log_file)
            res = run_tool(cmd, reporter, cancel)
            status = _status_from_tool(res)
            detail = res.summary() if not res.ok else f"Exportado: {xtf.name}"
            if res.ok and res.errors:
                status = ItemStatus.WARNING
            results.append(ItemResult(tgt.key, status, detail, log_file=log_file, output_file=str(xtf),
                                      duration=res.duration, errors=len(res.errors), warnings=len(res.warnings)))
            reporter.item(tgt.key, status, detail, log_file=log_file, output_file=str(xtf), duration=res.duration)
            reporter.log(f"{tgt.key}: {detail}", Level.SUCCESS if res.ok else Level.ERROR)
    except Cancelled:
        reporter.log("Proceso detenido por el usuario", Level.WARNING)
    except DatabaseError as exc:
        reporter.log(f"Error de base de datos: {exc}", Level.ERROR)
    done = {r.key for r in results}
    for tgt in req.targets:
        if tgt.key not in done:
            results.append(ItemResult(tgt.key, ItemStatus.CANCELLED))
            reporter.item(tgt.key, ItemStatus.CANCELLED)
    reporter.progress(total, total, "Exportación finalizada")
    _summary(reporter, results)
    return results
