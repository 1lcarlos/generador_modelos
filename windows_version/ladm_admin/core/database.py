"""Acceso a PostgreSQL/PostGIS e inspeccion de esquemas creados por ili2db."""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:  # pragma: no cover - se informa al usuario en tiempo de uso
    psycopg2 = None


class DatabaseError(Exception):
    pass


@dataclass
class ConnectionParams:
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = "postgres"
    password: str = ""

    def describe(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.database}"

    def with_database(self, database: str) -> "ConnectionParams":
        return ConnectionParams(self.host, self.port, database, self.user, self.password)


@dataclass
class SchemaInfo:
    name: str
    exists: bool = False
    is_ili2db: bool = False
    sender: str = ""                 # ej. ili2pg-5.5.1-<hash>
    basket_col: bool = False         # creado con --createBasketCol
    srs_code: str = ""
    models: list[str] = field(default_factory=list)          # nombres de modelo
    datasets: list[str] = field(default_factory=list)
    basket_count: int = 0
    table_count: int = 0             # tablas de datos (sin t_ili2db_*)
    settings: dict[str, str] = field(default_factory=dict)

    @property
    def ili2db_version(self) -> str:
        match = re.search(r"ili2(?:pg|db)-(\d+\.\d+\.\d+)", self.sender)
        return match.group(1) if match else ""

    @property
    def has_data(self) -> bool:
        return bool(self.datasets) or self.basket_count > 0


def _require_driver() -> None:
    if psycopg2 is None:
        raise DatabaseError("La libreria psycopg2 no está instalada (pip install psycopg2-binary)")


def _model_name(raw: str) -> str:
    """t_ili2db_model.modelname viene como 'Modelo{ Dep1 Dep2}'."""
    return raw.split("{", 1)[0].strip()


class Database:
    def __init__(self, params: ConnectionParams, connect_timeout: int = 8):
        self.params = params
        self.connect_timeout = connect_timeout

    # ------------------------------------------------------------------ conexión
    @contextmanager
    def connect(self, database: str | None = None, autocommit: bool = True):
        _require_driver()
        try:
            conn = psycopg2.connect(
                host=self.params.host,
                port=int(self.params.port),
                dbname=database or self.params.database or "postgres",
                user=self.params.user,
                password=self.params.password,
                connect_timeout=self.connect_timeout,
                application_name="LADMAdmin",
            )
        except psycopg2.OperationalError as exc:
            raise DatabaseError(str(exc).strip()) from exc
        if autocommit:
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            yield conn
        finally:
            conn.close()

    def test(self) -> dict:
        """Prueba la conexión. Devuelve versiones del servidor y de PostGIS."""
        target = self.params.database if self.database_exists() else "postgres"
        with self.connect(target) as conn, conn.cursor() as cur:
            cur.execute("SHOW server_version")
            server = cur.fetchone()[0]
            postgis = None
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            row = cur.fetchone()
            if row:
                postgis = row[0]
            cur.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'")
            postgis_available = cur.fetchone() is not None
        return {
            "server_version": server,
            "postgis_version": postgis,
            "postgis_available": postgis_available,
            "database_exists": target == self.params.database,
        }

    # ---------------------------------------------------------- base de datos
    def database_exists(self, name: str | None = None) -> bool:
        name = name or self.params.database
        with self.connect("postgres") as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            return cur.fetchone() is not None

    def create_database(self, name: str | None = None) -> None:
        name = name or self.params.database
        with self.connect("postgres") as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    def ensure_extensions(self, extensions=("postgis", "uuid-ossp")) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            for ext in extensions:
                cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext)))

    # ----------------------------------------------------------------- esquemas
    def list_schemas(self, only_ili2db: bool = False) -> list[str]:
        query = """
            SELECT n.nspname
            FROM pg_namespace n
            WHERE n.nspname NOT LIKE 'pg\\_%%'
              AND n.nspname NOT IN ('information_schema', 'public', 'topology', 'tiger', 'tiger_data')
        """
        if only_ili2db:
            query += """
              AND EXISTS (SELECT 1 FROM pg_class c
                          WHERE c.relnamespace = n.oid AND c.relname = 't_ili2db_settings')
            """
        query += " ORDER BY 1"
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(query)
            return [r[0] for r in cur.fetchall()]

    def schema_exists(self, schema: str) -> bool:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,))
            return cur.fetchone() is not None

    def drop_schema(self, schema: str) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))

    def rename_schema(self, old: str, new: str) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("ALTER SCHEMA {} RENAME TO {}").format(sql.Identifier(old), sql.Identifier(new)))

    def inspect_schema(self, schema: str) -> SchemaInfo:
        info = SchemaInfo(name=schema)
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,))
            info.exists = cur.fetchone() is not None
            if not info.exists:
                return info
            cur.execute(
                "SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = %s AND relname LIKE 't\\_ili2db\\_%%'",
                (schema,),
            )
            meta_tables = {r[0] for r in cur.fetchall()}
            info.is_ili2db = "t_ili2db_settings" in meta_tables
            cur.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = %s "
                "AND table_type = 'BASE TABLE' AND table_name NOT LIKE 't\_ili2db\_%%'",
                (schema,),
            )
            info.table_count = cur.fetchone()[0]
            if not info.is_ili2db:
                return info

            ident = sql.Identifier(schema)
            cur.execute(sql.SQL("SELECT tag, setting FROM {}.t_ili2db_settings").format(ident))
            info.settings = {tag: setting or "" for tag, setting in cur.fetchall()}
            info.sender = info.settings.get("ch.ehi.ili2db.sender", "")
            info.basket_col = info.settings.get("ch.ehi.ili2db.BasketHandling", "") == "readWrite"
            info.srs_code = info.settings.get("ch.ehi.ili2db.defaultSrsCode", "")

            if "t_ili2db_model" in meta_tables:
                cur.execute(sql.SQL("SELECT modelname FROM {}.t_ili2db_model").format(ident))
                names = [_model_name(r[0]) for r in cur.fetchall()]
                info.models = sorted(set(names))
            if "t_ili2db_dataset" in meta_tables:
                cur.execute(sql.SQL("SELECT datasetname FROM {}.t_ili2db_dataset ORDER BY 1").format(ident))
                info.datasets = [r[0] for r in cur.fetchall() if r[0] is not None]
            if "t_ili2db_basket" in meta_tables:
                cur.execute(sql.SQL("SELECT count(*) FROM {}.t_ili2db_basket").format(ident))
                info.basket_count = cur.fetchone()[0]
        return info

    def class_table_map(self, schema: str) -> dict[str, str]:
        """Nombre INTERLIS de clase -> tabla SQL (t_ili2db_classname)."""
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT iliname, sqlname FROM {}.t_ili2db_classname").format(sql.Identifier(schema))
            )
            return {ili: sqlname for ili, sqlname in cur.fetchall()}

    def count_rows(self, schema: str, tables: list[str], dataset: str | None = None) -> dict[str, int | None]:
        """Cuenta registros por tabla; si hay dataset filtra por sus baskets."""
        result: dict[str, int | None] = {}
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND column_name IN ('t_basket', 't_type')",
                (schema,),
            )
            cols: dict[str, set[str]] = {}
            for table, col in cur.fetchall():
                cols.setdefault(table, set()).add(col)
            for table in tables:
                if table not in cols and not self._table_exists(cur, schema, table):
                    result[table] = None
                    continue
                query = sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
                params: tuple = ()
                if dataset and "t_basket" in cols.get(table, set()):
                    query = sql.SQL(
                        "SELECT count(*) FROM {s}.{t} WHERE t_basket IN ("
                        "SELECT b.t_id FROM {s}.t_ili2db_basket b JOIN {s}.t_ili2db_dataset d "
                        "ON d.t_id = b.dataset WHERE d.datasetname = %s)"
                    ).format(s=sql.Identifier(schema), t=sql.Identifier(table))
                    params = (dataset,)
                cur.execute(query, params)
                result[table] = cur.fetchone()[0]
        return result

    @staticmethod
    def _table_exists(cur, schema: str, table: str) -> bool:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
        return cur.fetchone() is not None
