# Arquitectura y guía de desarrollo

Guía para quien mantenga o extienda la herramienta. Las razones de cada decisión están en
[decisiones.md](decisiones.md) y lo pendiente en [estado_implementacion.md](estado_implementacion.md).

---

## 1. Vista general

```
                ┌──────────────────────────┐     ┌─────────────────────┐
  Usuario ───►  │ ui/ (PySide6)            │     │ cli.py (argparse)   │
                │ páginas, diálogos, tema  │     │                     │
                └────────────┬─────────────┘     └──────────┬──────────┘
                             │ solicitudes + Reporter + CancelToken
                             ▼                              ▼
                ┌────────────────────────────────────────────────────────┐
                │ core/operations.py  validar · crear · importar · exportar│
                ├────────────────────────────────────────────────────────┤
                │ ili2db.py  comandos   │ process.py  ejecución Java      │
                │ database.py  PostgreSQL / t_ili2db_*                    │
                │ xtf.py  ili.py  naming.py  settings.py  tools_setup.py  │
                └──────────────┬───────────────────────┬─────────────────┘
                               ▼                       ▼
                  java -jar ili2pg / ilivalidator    PostgreSQL + PostGIS (psycopg2)
```

**Regla principal:** `core/` no importa nada de Qt. La interfaz y el CLI construyen una *solicitud*
(dataclass), llaman a una función `run_*` y reciben eventos por un `Reporter`.

---

## 2. Módulos

### `ladm_admin/core/`

| Módulo | Responsabilidad |
|--------|-----------------|
| `operations.py` | Las cuatro operaciones: `run_validation`, `run_create` (+ `check_create_request`), `analyze_import` / `reevaluate_import` / `evaluate_item` / `run_import`, `list_export_targets` / `run_export`. Devuelven `list[ItemResult]`. |
| `ili2db.py` | Catálogo de opciones de `--schemaimport` (`SCHEMA_OPTIONS`), `ImportMode` y constructores de comandos `Ili2pg` / `Ilivalidator`. |
| `process.py` | `run_tool`: ejecuta Java sin shell, transmite la salida al `Reporter`, clasifica líneas, permite cancelar. `ToolResult.main_error()` extrae la causa útil. `mask_command` oculta `--dbpwd`. |
| `database.py` | `Database`: conexión, creación de base y extensiones, `inspect_schema` (lee `t_ili2db_settings`, `_model`, `_dataset`, `_basket`), renombrar y borrar esquemas, conteos por tabla y dataset. |
| `xtf.py` | Lectura en streaming de XTF 2.3/2.4: `read_header` (rápido) y `scan_content` (baskets y objetos por clase). `expand_sources` convierte carpetas y ZIP en `SourceFile`. |
| `ili.py` | Lectura liviana de `.ili`: modelos, tipo, versión, IMPORTS; `suggested_models`, `duplicate_models`. |
| `naming.py` | `StorageMode`, `NamingConvention` (prefijo ↔ código) y `code_from_path`. |
| `settings.py` | `AppSettings`, `ConnectionProfile`, `ModelProfile`; persistencia en JSON; contraseñas en keyring; migración desde 2.0. |
| `tools_setup.py` | Descarga e instalación verificada de ili2pg/ilivalidator (`PACKAGES` con URL y SHA-256). |
| `events.py` | `Level`, `ItemStatus`, `Reporter` (base y consola), `CancelToken`, `Cancelled`. |
| `paths.py` | Rutas de la aplicación, versiones fijadas, búsqueda de Java. |
| `reports.py` | Lectura del CSV de ilivalidator y escritura de resúmenes CSV. |

### `ladm_admin/ui/`

| Módulo | Responsabilidad |
|--------|-----------------|
| `app.py` | Arranque: `QApplication`, tema, ventana. |
| `main_window.py` | Barra lateral, encabezado (conexión y perfil activos), páginas, cierre seguro. `deliver()` pasa datos entre páginas. |
| `context.py` | `AppContext`: configuración compartida, señales (`connectionChanged`, `profileChanged`, `busyChanged`, `navigateRequested`), contraseña bajo demanda. |
| `worker.py` | `Job` (hilo de trabajo), `QtReporter` (eventos → señales), `DecisionBridge` (el hilo pregunta al usuario y espera). |
| `pages/base.py` | `OperationPage`: formulario + Resultados/Registro + barra de ejecución; `run_job`, `run_helper`, decisiones. |
| `pages/*.py` | `home`, `validate`, `create`, `import_`, `export`, `settings`. |
| `widgets.py` | Componentes reutilizables: `Card`, `Banner`, `PathEdit`, `DropArea`, `DataTable`, `ResultsTable`, `LogView`, `RunBar`, `Collapsible`. |
| `dialogs.py` | Contraseña, esquema existente, conflicto de importación y tabla de errores de validación. |
| `theme.py`, `icons.py` | Paleta clara/oscura con su hoja de estilos; iconos SVG en línea. |

---

## 3. Flujo de una operación

Ejemplo: importar desde la interfaz.

1. `ImportPage.add_paths` → `expand_sources` → `analyze` (en un `run_helper`, fuera del hilo de la
   interfaz) → `analyze_import` lee cabeceras y conteos e inspecciona la base → la tabla muestra el plan.
2. Al editar el esquema o el dataset se programa `_reevaluate`, que vuelve a llamar a `analyze`.
3. `start()` arma un `ImportRequest` y llama a `run_job(run_import, req, items, decide=...)`.
4. `run_import` corre en un `Job`:
   - emite `reporter.log/progress/item`; `QtReporter` los convierte en señales;
   - ante un conflicto con la política *Preguntar*, llama a `decide(item)`. Esa función usa
     `DecisionBridge.ask`, que emite una señal; la página muestra el diálogo en el hilo principal y el
     hilo de trabajo espera la respuesta;
   - para cada archivo ejecuta `run_tool(ili2pg.data_import(...))` y luego `_verify`.
5. Al terminar, `Job.finished` → `_on_finished` → resumen y `on_results`.

**Cancelación:** `CancelToken.cancel()` marca la bandera y mata el proceso Java en curso. Las operaciones
revisan `cancel.raise_if_cancelled()` entre elementos.

---

## 4. Convenciones

- **Idioma:** textos visibles en español con tildes. Son **ASCII** las opciones del CLI, los
  `objectName` y selectores de la hoja de estilos, las claves de configuración y los nombres de archivos
  y carpetas generados ([D19](decisiones.md#d19---idioma-y-convenciones-de-texto)).
- **Hilos:** nunca tocar widgets desde un `Job`; usar el `Reporter` o señales. Las consultas cortas a la
  base desde la interfaz van en `run_helper`.
- **Errores al usuario:** mensajes que digan qué pasó y qué hacer ("El esquema X no existe. Créelo
  primero en 'Crear esquema'").
- **Nada destructivo sin confirmación:** las operaciones que borran o reemplazan se confirman o siguen la
  política elegida por el usuario.
- **Secretos:** las contraseñas solo pasan por `settings.get_password` / `set_password` y se enmascaran
  con `mask_command`.

---

## 5. Cómo extender

**Agregar una opción de `--schemaimport`:** añadir un `SchemaOption` en `core/ili2db.SCHEMA_OPTIONS`. La
interfaz de perfiles la muestra automáticamente en su grupo.

**Agregar una política de importación** (por ejemplo `--update`):
1. un valor en `ImportMode`;
2. su rama en `run_import`;
3. el botón de radio en `ui/pages/import_.py` y la opción en `ask_import_conflict`;
4. la opción `--si-hay-datos` en `cli.py`;
5. pruebas y manual.

**Agregar una operación nueva:**
1. dataclass de solicitud + `run_x(req, reporter, cancel) -> list[ItemResult]` en `core/operations.py`;
2. pruebas en `tests/`;
3. subcomando en `cli.py`;
4. página nueva heredando de `OperationPage` (`build_form`, `start`) y registrada en `MainWindow` y
   `NAV`.

**Actualizar ili2pg o ilivalidator:**
1. cambiar la versión en `core/paths.py`;
2. calcular el SHA-256 del ZIP oficial y actualizar `core/tools_setup.PACKAGES`;
3. revisar `ejecutar_administrador.bat`, que tiene las rutas de los JAR;
4. probar crear, importar y exportar contra una base de pruebas;
5. actualizar la documentación.

---

## 6. Pruebas

```cmd
cd windows_version
python -m pip install -r requirements-dev.txt
python -m pytest tests
```

| Archivo | Cubre |
|---------|-------|
| `tests/test_core.py` | Lectura de ILI y XTF (incluidos ZIP), nombres, clasificación de líneas, mensajes de error, comandos ili2pg, estados del plan de importación |
| `tests/test_tools_setup.py` | Instalación desde ZIP, huella incorrecta, rutas peligrosas, versiones fijadas |
| `tests/test_cli.py` | Los comandos documentados se interpretan; opciones ASCII; la documentación solo usa opciones existentes |

GitHub Actions (`.github/workflows/pruebas.yml`) ejecuta las pruebas en Windows con Python 3.10 y 3.12,
sin PySide6; la interfaz solo se compila. Las pruebas contra PostgreSQL y de la interfaz todavía se hacen
a mano ([estado §4](estado_implementacion.md#4-cómo-se-verificó)).

---

## 7. Configuración y archivos en tiempo de ejecución

| Ubicación | Contenido |
|-----------|-----------|
| `%APPDATA%\LADMAdmin\settings.json` | `AppSettings` serializado (sin contraseñas) |
| Administrador de credenciales, servicio `LADMAdmin` | Contraseñas, con clave `usuario@host:puerto/base` |
| `%LOCALAPPDATA%\LADMAdmin\trabajo\` | XTF extraídos de ZIP |
| `windows_version\log\` (configurable) | `crear_esquema\`, `importar\` |
| `windows_version\ili2pg\` | Herramientas descargadas |
| `%USERPROFILE%\.ili2pg_gui\` | Perfiles de la versión 2.0 (solo lectura, para migrar) |

---

## 8. Capturas del manual

Las imágenes de `docs/img/` se generan con `windows_version/scripts/capturas_manual.py`, que recorre la
aplicación sin pantalla con datos de ejemplo:

```cmd
set LADM_PGPASSWORD=...
python scripts\capturas_manual.py --ejemplos D:\ejemplos --salida ..\docs\img --port 5432
```

- La base indicada (por defecto `catastro`) **no debe existir**. El script la crea al crear esquemas y se
  niega a usar una existente. Elimínela al terminar.
- Para no mostrar rutas personales, ejecútelo desde una copia de la aplicación en una ruta neutra (por
  ejemplo `C:\LADMAdmin`).
- Los archivos de ejemplo requeridos se describen en el encabezado del script.

---

## 9. Versionado y publicación

- Ramas de trabajo `version-X.Y` → PR a `master`. Las versiones publicadas se etiquetan (`v2.0`; la 3.0
  se etiquetará al fusionar).
- La versión de la aplicación está en `ladm_admin/__init__.py` (`__version__`) y se muestra en la barra
  lateral.
- Registrar los cambios en `CHANGELOG.md`.
- No se suben datos XTF, logs, ZIP, `ili2pg/` ni el modelo interno ACC (ver `.gitignore` y
  [D20](decisiones.md#d20---datos-y-modelo-interno-fuera-del-repositorio)).
