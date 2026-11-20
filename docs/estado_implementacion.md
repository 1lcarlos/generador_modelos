# Estado de la implementación

**Versión:** 3.0.0 · **Actualizado:** 2026-11-20 · **Rama:** `version-3.0` (pendiente de fusionar en `master`)

Resume qué está construido, cómo se verificó, qué limitaciones se conocen y qué falta. Las razones de cada
decisión están en [decisiones.md](decisiones.md); la organización del código, en
[arquitectura.md](arquitectura.md).

---

## 1. Resumen

| Área | Estado |
|------|--------|
| Validar XTF | ✅ Completo y verificado con datos reales |
| Crear esquema | ✅ Completo y verificado (SINIC: 90 tablas; Interno ACC: 150 tablas) |
| **Importar XTF** | ✅ Completo y verificado: plan, tres políticas de conflicto, verificación de conteos |
| Exportar XTF | ✅ Completo y verificado (por esquema y por dataset) |
| Interfaz PySide6 | ✅ Completa; probada de punta a punta sin pantalla (offscreen) |
| Línea de comandos | ✅ Completa; los comandos documentados están cubiertos por pruebas |
| Descarga de herramientas | ✅ Verificada desde cero contra `downloads.interlis.ch` |
| Migración desde la 2.0 | ✅ Importa conexiones y perfiles; contraseñas al keyring |
| Pruebas automáticas | ✅ 26 pruebas unitarias + GitHub Actions (Windows, Python 3.10/3.12) |
| Pruebas de integración automatizadas | ⏳ Pendiente (hoy se verifica a mano, ver §4) |
| Instalador / ejecutable | ⏳ Pendiente |
| Prevalidación de reglas SINIC | ⏸ Fuera de alcance por decisión ([D15](decisiones.md#d15---sin-prevalidación-de-reglas-sinic)) |

---

## 2. Funcionalidad implementada

### Validar XTF (`core/operations.run_validation`, `ui/pages/validate.py`)
- Entradas: archivos `.xtf`, `.zip` (se extraen a `%LOCALAPPDATA%\LADMAdmin\trabajo`) y carpetas
  recursivas.
- Lectura de cabecera (modelos, emisor) para INTERLIS 2.3 y 2.4. La 2.4 está implementada pero **no se
  ha probado con archivos reales**.
- ilivalidator con `--log` y `--csvlog`, y opcionalmente `--xtflog` y `--allObjectsAccessible`.
- Tabla filtrable de errores (`ui/dialogs.IssuesDialog`) a partir del CSV.
- Botón para enviar los archivos válidos a Importar.

### Crear esquema (`run_create`, `ui/pages/create.py`)
- Por municipio (`<prefijo><código>`) o esquema único.
- Crea la base de datos si no existe, y las extensiones `postgis` y `uuid-ossp`.
- Si el esquema existe: preguntar, omitir, actualizar o recrear. Recrear usa respaldo y restauración.
- Verificación previa en la base: si existe, versión de ili2pg, tablas y datasets.
- Vista previa del comando, con la contraseña enmascarada.

### Importar XTF (`analyze_import`, `reevaluate_import`, `run_import`, `ui/pages/import_.py`)
- Plan con estados *Listo*, *Ya tiene datos* y *Bloqueado*. Bloquea por:
  - esquema inexistente o que no es ili2db;
  - modelos ausentes en el esquema;
  - clases sin tabla;
  - destino duplicado en el lote;
  - esquema único sin columna de basket.
- Edición del esquema y del dataset en el plan, y exclusión de archivos.
- Políticas: reemplazar, agregar como nuevo dataset, no importar, preguntar.
- Opciones: validar durante la importación, verificar conteos, omitir errores de referencia o de
  geometría.
- Los bloqueados se reportan como error ([D21](decisiones.md#d21---los-archivos-bloqueados-se-reportan-como-error)).

### Exportar XTF (`run_export`, `ui/pages/export.py`)
- Lista los esquemas ili2db (filtro por prefijo) o los datasets de un esquema único.
- Genera `<salida>/<código>/<código>.xtf` y `<código>_exportacion.log`, con `--exportTid` por defecto.
- Botón para enviar los archivos exportados a Validar.

### Transversal
- Conexiones y perfiles de modelo persistentes (`%APPDATA%\LADMAdmin\settings.json`), con las
  contraseñas en el keyring.
- Página de Inicio con el estado del entorno: Java, JAR, base de datos y perfil.
- Registro filtrable, resultados con acceso a los logs, cancelación real del proceso Java.
- Tema claro, oscuro y del sistema.

---

## 3. Entorno verificado

| Componente | Versión probada |
|------------|-----------------|
| Windows | 11 Pro |
| Python | 3.10.8 |
| PySide6 | 6.8.3 |
| Java | 1.8.0_221 |
| ili2pg / ilivalidator | 5.5.1 / 1.15.0 |
| PostgreSQL / PostGIS | 12.16 / 3.4.2 |

Datos de prueba: entregas reales de los municipios 25019, 25279, 25436 (modelo Interno ACC) y 25645
(SINIC). No están en el repositorio.

---

## 4. Cómo se verificó

| Verificación | Resultado |
|--------------|-----------|
| Pruebas unitarias (`python -m pytest tests`) | 26 pruebas: XTF, ILI, nombres, comandos, plan de importación, instalador, CLI y documentación |
| Integración contra PostgreSQL (manual) | Crear (SINIC/ACC) → importar 25279 (1.520 objetos, conteos coinciden) → reemplazar → agregar (falla por UNIQUE, sin datos parciales) → exportar → validar lo exportado |
| Recrear con fallo provocado | El esquema original se restauró con sus datos |
| Interfaz de punta a punta (offscreen) | Validar → crear → importar (reemplazar) → exportar desde las páginas, con hilos y señales reales |
| Descarga de herramientas | Instalación desde cero; SHA-256 idénticos a los ZIP previos |
| Clon limpio del repositorio | Pruebas y CLI funcionan sin archivos locales |

**Verificación manual sugerida antes de publicar una versión:**
1. `python -m pytest tests`.
2. En una base de pruebas: crear `cun25279`, importar su XTF y verificar *conteos coinciden*.
3. Reimportar con *Reemplazar* y luego con *Agregar* (debe fallar sin dejar datos parciales).
4. Exportar y validar el XTF exportado.
5. Abrir cada página en tema claro y oscuro.

---

## 5. Limitaciones conocidas

| Limitación | Impacto | Referencia |
|------------|---------|------------|
| La contraseña viaja en `--dbpwd` | Visible en el administrador de tareas mientras corre Java | [D10](decisiones.md#d10---contraseñas-en-keyring-y---dbpwd) |
| Reemplazar en modo por municipio borra los otros datasets en llamadas separadas | Si falla la importación posterior, esos otros datasets ya fueron borrados (el del municipio se conserva) | [D06](decisiones.md#d06---políticas-ante-datos-existentes) |
| La verificación de conteos no compara estructuras | Diferencias en elementos estructurados no se detectan | [D13](decisiones.md#d13---análisis-previo-y-verificación-de-conteos) |
| "Ir a Importar" envía el ZIP completo | Si el ZIP trae varios XTF, se agregan todos, incluso los no validados | `ui/pages/validate.py::_go_import` |
| Mensajes del servidor PostgreSQL con `?`/`�` | Servidores en español con codificación WIN1252 antes de negociar UTF-8; solo es cosmético | — |
| `%LOCALAPPDATA%\LADMAdmin\trabajo` no se limpia | Crece con cada ZIP procesado | — |
| La interfaz no tiene pruebas automatizadas | Las regresiones visuales se detectan a mano | — |
| INTERLIS 2.4 sin probar con datos reales | Posibles errores de lectura de cabecera o conteo | `core/xtf.py` |

---

## 6. Pendientes priorizados

### Prioridad alta
1. **Revisar y fusionar el PR `version-3.0` → `master`.** Confirmar que GitHub Actions pasa.
2. **Recrear los esquemas antiguos** (`sinic_ladm`, creados con 4.4.3 y sin basket) con la 3.0, o
   documentar que se abandonan.
3. **Ejecutable para usuarios finales**: PyInstaller con un JRE incluido (carpeta `jre/`, que
   `core/paths.find_java` ya busca) para no exigir Python ni Java. Evaluar si `ili2pg/` se empaqueta o se
   descarga.
4. **Definir la licencia** del repositorio (decisión institucional de la ACC).

### Prioridad media
5. **Pruebas de integración automatizadas** con PostgreSQL+PostGIS: marcador `pytest -m integracion` que
   se active con una variable de entorno, por ejemplo `LADM_TEST_DSN`, y servicio PostGIS en CI (runner
   Ubuntu).
6. **Pruebas de humo de la interfaz** con `pytest-qt` en modo offscreen: abrir cada página y ejecutar un
   flujo con base de pruebas.
7. **"Ir a Importar"** debería enviar solo los XTF válidos, no el ZIP completo.
8. **Limpieza de la carpeta de trabajo** (ZIP extraídos), al cerrar la aplicación o con un botón.
9. **Exportar el resumen de resultados a CSV** desde la interfaz. `core/reports.write_results_csv` ya
   existe; falta el botón.
10. **Corregir el archivo duplicado del modelo interno ACC** (`Submodelo_Valoracion_Masiva_V1_0.ili` y
    `..._v_1_0.ili` definen el mismo modelo). Es un problema de la carpeta de modelos, no del código.

### Prioridad baja / a evaluar
11. Prevalidación de reglas de negocio SINIC con consultas SQL después de importar (hoy fuera de alcance,
    [D15](decisiones.md#d15---sin-prevalidación-de-reglas-sinic)).
12. Modo `--update` de ili2db (sincronizar por OID) como cuarta política.
13. Exportar e importar perfiles y conexiones entre equipos (sin contraseñas).
14. Probar y documentar el soporte de INTERLIS 2.4.
15. Mover la aplicación a la raíz del repositorio; se decidió mantener `windows_version/`
    ([D16](decisiones.md#d16---retiro-de-la-versión-20-y-estructura-del-repositorio)).

---

## 7. Cómo continuar el desarrollo

```cmd
git clone https://github.com/1lcarlos/generador_modelos.git
cd generador_modelos\windows_version
python -m pip install -r requirements-dev.txt
python -m ladm_admin herramientas      :: descarga ili2pg/ilivalidator
python -m pytest tests
python -m ladm_admin                   :: interfaz
```

- Lea [arquitectura.md](arquitectura.md) antes de modificar el código.
- Toda lógica nueva va en `core/` con su prueba en `tests/`; la interfaz solo la invoca.
- Si cambia el comportamiento visible, actualice el [manual de usuario](manual_usuario.md) y el
  [CHANGELOG](../CHANGELOG.md).
- Si toma una decisión de diseño, regístrela en [decisiones.md](decisiones.md).
- Para regenerar las capturas del manual se usa la aplicación con datos de ejemplo; ver
  [arquitectura.md §8](arquitectura.md#8-capturas-del-manual).
