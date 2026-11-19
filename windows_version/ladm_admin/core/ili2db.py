"""Construccion de comandos para ili2pg e ilivalidator.

Nota: ili2db solo acepta la contraseña por ``--dbpwd`` (se probó ``--dbparams``
y ``PGPASSFILE``: ambos son ignorados). En logs y pantalla se enmascara.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .database import ConnectionParams


@dataclass(frozen=True)
class SchemaOption:
    flag: str
    label: str
    description: str
    group: str
    default: bool = True


# Opciones de --schemaimport. Los valores por defecto son los recomendados para LADM-COL.
SCHEMA_OPTIONS: list[SchemaOption] = [
    SchemaOption("createBasketCol", "Columna de basket (t_basket)",
                 "Necesaria para importar por dataset, reemplazar datos y manejar varios municipios en un esquema.",
                 "Datasets"),
    SchemaOption("createDatasetCol", "Columna de dataset (t_datasetname)",
                 "Guarda en cada tabla el nombre del dataset (municipio) al que pertenece el registro.",
                 "Datasets"),
    SchemaOption("createTidCol", "Columna TID (t_ili_tid)",
                 "Conserva el identificador de transferencia (UUID) de cada objeto.", "Identificadores"),
    SchemaOption("smart2Inheritance", "Herencia smart2",
                 "Una tabla por clase concreta; mapeo recomendado para LADM-COL.", "Estructura"),
    SchemaOption("createEnumTabs", "Tablas de dominios",
                 "Crea una tabla por cada dominio (enumeración).", "Dominios"),
    SchemaOption("createEnumTabsWithId", "Dominios con ID",
                 "Las tablas de dominio tienen llave t_id y las clases las referencian por FK.", "Dominios"),
    SchemaOption("beautifyEnumDispName", "Nombres legibles en dominios",
                 "Reemplaza '_' por espacios en el texto visible de los dominios.", "Dominios"),
    SchemaOption("coalesceCatalogueRef", "Unificar referencias a catálogo",
                 "Mapea las referencias a catálogos como una FK simple.", "Estructura"),
    SchemaOption("coalesceMultiSurface", "Unificar MultiSurface",
                 "Usa una columna de geometría MULTIPOLYGON.", "Geometria"),
    SchemaOption("coalesceMultiLine", "Unificar MultiLine",
                 "Usa una columna de geometría MULTILINESTRING.", "Geometria"),
    SchemaOption("coalesceMultiPoint", "Unificar MultiPoint",
                 "Usa una columna de geometría MULTIPOINT.", "Geometria"),
    SchemaOption("coalesceArray", "Unificar arreglos",
                 "Mapea BAG OF de tipos simples como arreglos.", "Estructura"),
    SchemaOption("strokeArcs", "Segmentar arcos",
                 "Convierte arcos en segmentos de recta.", "Geometria"),
    SchemaOption("expandMultilingual", "Expandir textos multilingües",
                 "Una columna por idioma para los textos multilingües.", "Estructura"),
    SchemaOption("createGeomIdx", "Índices espaciales",
                 "Crea índices GiST sobre las columnas de geometría.", "Restricciones e índices"),
    SchemaOption("createFk", "Llaves foraneas",
                 "Crea restricciones de llave foranea.", "Restricciones e índices"),
    SchemaOption("createFkIdx", "Índices de llaves foraneas",
                 "Crea índices sobre las columnas de llave foranea.", "Restricciones e índices"),
    SchemaOption("createUnique", "Restricciones UNIQUE",
                 "Crea las restricciones de unicidad definidas en el modelo.", "Restricciones e índices"),
    SchemaOption("createNumChecks", "Validaciones numéricas",
                 "Crea CHECK para los rangos numericos del modelo.", "Restricciones e índices"),
    SchemaOption("createTypeConstraint", "Restriccion de tipo",
                 "Valida el tipo de objeto en tablas con herencia.", "Restricciones e índices"),
    SchemaOption("createMetaInfo", "Metainformación",
                 "Crea tablas con metadatos del modelo (usadas por QGIS Model Baker).", "Metadatos"),
    SchemaOption("setupPgExt", "Configurar extensiones",
                 "Crea las extensiones PostgreSQL requeridas (uuid-ossp).", "Metadatos"),
    SchemaOption("sqlEnableNull", "Permitir NULL en atributos obligatorios",
                 "Requerido si se importara con 'Omitir errores de referencia'.", "Restricciones e índices",
                 default=False),
]

SCHEMA_OPTION_FLAGS = {opt.flag for opt in SCHEMA_OPTIONS}


def default_schema_options() -> dict[str, bool]:
    return {opt.flag: opt.default for opt in SCHEMA_OPTIONS}


class ImportMode(str, Enum):
    """Acción cuando el destino ya contiene datos."""

    REPLACE = "reemplazar"
    APPEND = "agregar"
    CANCEL = "cancelar"
    ASK = "preguntar"

    @property
    def label(self) -> str:
        return {
            ImportMode.REPLACE: "Reemplazar los datos existentes",
            ImportMode.APPEND: "Agregar como un nuevo dataset",
            ImportMode.CANCEL: "No importar (omitir)",
            ImportMode.ASK: "Preguntar en cada caso",
        }[self]


@dataclass
class ToolConfig:
    java: str
    ili2pg_jar: str
    ilivalidator_jar: str = ""
    java_max_memory: str = ""  # ej. "4g"; vacío = valor por defecto de la JVM

    def java_cmd(self, jar: str) -> list[str]:
        cmd = [self.java]
        if self.java_max_memory:
            cmd.append(f"-Xmx{self.java_max_memory}")
        cmd.extend(["-jar", jar])
        return cmd


@dataclass
class Ili2pg:
    tools: ToolConfig
    conn: ConnectionParams
    modeldir: str = ""

    def _base(self, action: str, schema: str) -> list[str]:
        cmd = self.tools.java_cmd(self.tools.ili2pg_jar) + [
            action,
            "--dbhost", self.conn.host,
            "--dbport", str(self.conn.port),
            "--dbdatabase", self.conn.database,
            "--dbusr", self.conn.user,
            "--dbschema", schema,
        ]
        if self.conn.password:
            cmd += ["--dbpwd", self.conn.password]
        if self.modeldir:
            # %ILI_FROM_DB permite resolver modelos ya guardados en el esquema.
            cmd += ["--modeldir", f"{self.modeldir};%ILI_FROM_DB"]
        return cmd

    def schema_import(
        self,
        schema: str,
        models: list[str],
        srs_code: str,
        options: dict[str, bool],
        prescript: str = "",
        log_file: str = "",
    ) -> list[str]:
        cmd = self._base("--schemaimport", schema)
        cmd += ["--defaultSrsAuth", "EPSG", "--defaultSrsCode", str(srs_code)]
        for flag, enabled in options.items():
            if enabled and flag in SCHEMA_OPTION_FLAGS:
                cmd.append(f"--{flag}")
        if prescript:
            cmd += ["--preScript", prescript]
        if log_file:
            cmd += ["--log", log_file]
        cmd += ["--models", ";".join(models)]
        return cmd

    def data_import(
        self,
        schema: str,
        xtf: str,
        models: list[str] | None = None,
        dataset: str | None = None,
        replace: bool = False,
        import_tid: bool = True,
        import_bid: bool = True,
        disable_validation: bool = False,
        skip_reference_errors: bool = False,
        skip_geometry_errors: bool = False,
        strokeArcs: bool = True,
        log_file: str = "",
        xtflog: str = "",
    ) -> list[str]:
        cmd = self._base("--replace" if replace else "--import", schema)
        if dataset:
            cmd += ["--dataset", dataset]
        if models:
            cmd += ["--models", ";".join(models)]
        if import_tid:
            cmd.append("--importTid")
        if import_bid:
            cmd.append("--importBid")
        if strokeArcs:
            cmd.append("--strokeArcs")
        if disable_validation:
            cmd.append("--disableValidation")
        if skip_reference_errors:
            cmd.append("--skipReferenceErrors")
        if skip_geometry_errors:
            cmd.append("--skipGeometryErrors")
        if log_file:
            cmd += ["--log", log_file]
        if xtflog:
            cmd += ["--xtflog", xtflog]
        cmd.append(xtf)
        return cmd

    def delete_dataset(self, schema: str, dataset: str, log_file: str = "") -> list[str]:
        cmd = self._base("--delete", schema) + ["--dataset", dataset]
        if log_file:
            cmd += ["--log", log_file]
        return cmd

    def export(
        self,
        schema: str,
        xtf: str,
        models: list[str] | None = None,
        dataset: str | None = None,
        export_tid: bool = True,
        disable_validation: bool = False,
        log_file: str = "",
    ) -> list[str]:
        cmd = self._base("--export", schema)
        if dataset:
            cmd += ["--dataset", dataset]
        elif models:
            cmd += ["--models", ";".join(models)]
        if export_tid:
            cmd.append("--exportTid")
        if disable_validation:
            cmd.append("--disableValidation")
        if log_file:
            cmd += ["--log", log_file]
        cmd.append(xtf)
        return cmd


@dataclass
class Ilivalidator:
    tools: ToolConfig
    modeldir: str = ""
    extra_args: list[str] = field(default_factory=list)

    def validate(
        self,
        xtf: str,
        models: list[str] | None = None,
        log_file: str = "",
        xtflog: str = "",
        csvlog: str = "",
        config_file: str = "",
        all_objects_accessible: bool = False,
    ) -> list[str]:
        cmd = self.tools.java_cmd(self.tools.ilivalidator_jar)
        if self.modeldir:
            cmd += ["--modeldir", self.modeldir]
        if models:
            cmd += ["--models", ";".join(models)]
        if all_objects_accessible:
            cmd.append("--allObjectsAccessible")
        if config_file:
            cmd += ["--config", config_file]
        if log_file:
            cmd += ["--log", log_file]
        if xtflog:
            cmd += ["--xtflog", xtflog]
        if csvlog:
            cmd += ["--csvlog", csvlog]
        cmd += self.extra_args
        cmd.append(xtf)
        return cmd


def ensure_parent(path: str | Path) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return str(path)
