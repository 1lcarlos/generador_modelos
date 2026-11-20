# Registro de decisiones

Decisiones de diseño de la versión 3.0, con su contexto y consecuencias. Antes de cambiar algo de lo que
aquí se describe, lea la decisión correspondiente; si se toma una nueva decisión, agréguela al final con
el siguiente número.

**Formato:** contexto → decisión → alternativas descartadas → consecuencias.
**Estados:** *Vigente*, *Reemplazada por DNN*, *Pendiente de revisión*.

| # | Decisión | Fecha | Estado |
|---|----------|-------|--------|
| [D01](#d01---reescribir-con-un-núcleo-separado-de-la-interfaz) | Núcleo separado de la interfaz | 2026-11-19 | Vigente |
| [D02](#d02---interfaz-en-pyside6) | Interfaz en PySide6 | 2026-11-19 | Vigente |
| [D03](#d03---una-sola-versión-de-ili2pg-551) | Una sola versión de ili2pg (5.5.1) | 2026-11-19 | Vigente |
| [D04](#d04---dos-modos-de-almacenamiento) | Dos modos de almacenamiento | 2026-11-19 | Vigente |
| [D05](#d05---la-importación-no-crea-esquemas) | La importación no crea esquemas | 2026-11-19 | Vigente |
| [D06](#d06---políticas-ante-datos-existentes) | Políticas ante datos existentes | 2026-11-19 | Vigente |
| [D07](#d07---dataset--código-divipola-y-prefijo-configurable) | Dataset = código DIVIPOLA | 2026-11-19 | Vigente |
| [D08](#d08---columna-de-basket-obligatoria-en-la-práctica) | Columna de basket obligatoria | 2026-11-19 | Vigente |
| [D09](#d09---pasar-todos-los-modelos-con-contenido-a---models) | Todos los modelos con contenido en `--models` | 2026-11-19 | Vigente |
| [D10](#d10---contraseñas-en-keyring-y---dbpwd) | Contraseñas en keyring y `--dbpwd` | 2026-11-19 | Vigente |
| [D11](#d11---recrear-con-respaldo-y-restauración) | Recrear con respaldo y restauración | 2026-11-19 | Vigente |
| [D12](#d12---ejecutar-java-sin-shell) | Ejecutar Java sin shell | 2026-11-19 | Vigente |
| [D13](#d13---análisis-previo-y-verificación-de-conteos) | Análisis previo y verificación de conteos | 2026-11-19 | Vigente |
| [D14](#d14---herramientas-descargadas-con-huella-fija) | Herramientas descargadas con huella fija | 2026-11-19 | Vigente |
| [D15](#d15---sin-prevalidación-de-reglas-sinic) | Sin prevalidación de reglas SINIC | 2026-11-19 | Vigente |
| [D16](#d16---retiro-de-la-versión-20-y-estructura-del-repositorio) | Retiro de la 2.0 y estructura del repositorio | 2026-11-19 | Vigente |
| [D17](#d17---exportación-con-los-modelos-del-esquema) | Exportación con los modelos del esquema | 2026-11-19 | Vigente |
| [D18](#d18---validación-con-modelos-de-la-cabecera-y-reporte-csv) | Validación con modelos de la cabecera | 2026-11-19 | Vigente |
| [D19](#d19---idioma-y-convenciones-de-texto) | Idioma y convenciones de texto | 2026-11-19 | Vigente |
| [D20](#d20---datos-y-modelo-interno-fuera-del-repositorio) | Datos y modelo interno fuera del repositorio | 2026-11-19 | Vigente |
| [D21](#d21---los-archivos-bloqueados-se-reportan-como-error) | Bloqueados se reportan como error | 2026-11-20 | Vigente |

---

## D01 - Reescribir con un núcleo separado de la interfaz

**Contexto.** La versión 2.0 era una clase Tkinter de 2.200 líneas que mezclaba interfaz, comandos y
acceso a la base. El CLI (`creacion_modelos_fisicos.py`) duplicaba la lógica, y ya había divergido: usaba
ili2pg 4.4.3 mientras la interfaz usaba 5.5.1.

**Decisión.** Paquete `ladm_admin` con tres capas:
- `core/`: sin dependencias de Qt; las operaciones reciben una solicitud, un `Reporter` y un
  `CancelToken`.
- `ui/`: solo presentación.
- `cli.py`: solo argumentos.

**Alternativas.** Corregir la 2.0 incrementalmente; se descartó porque la duplicación y el acoplamiento
seguirían.

**Consecuencias.** La interfaz y el CLI se comportan igual. El núcleo se prueba sin interfaz. Toda regla
nueva va en `core/`.

## D02 - Interfaz en PySide6

**Contexto.** Se buscaba una herramienta "profesional y verdadera": tablas con casillas y edición,
trabajo en segundo plano seguro y aspecto moderno.

**Decisión.** PySide6 6.8 (Qt 6), con tema propio claro/oscuro (`ui/theme.py`) e iconos SVG en línea.

**Alternativas.**
- Tkinter + ttkbootstrap: más liviano, pero limitado en tablas y estilos.
- Interfaz web: exige servidor y despliegue.

**Consecuencias.** Dependencia de unos 150 MB. Empaquetar como `.exe` requiere PyInstaller (pendiente).
Los widgets solo se tocan desde el hilo principal: los hilos de trabajo comunican por señales
(`ui/worker.py`).

## D03 - Una sola versión de ili2pg (5.5.1)

**Contexto.** Convivían ili2pg 4.4.3 y 5.5.1. Usar una versión para crear el esquema y otra para importar
o exportar puede fallar por diferencias en las tablas `t_ili2db_*`. No hay esquemas en producción creados
con 4.4.3.

**Decisión.** Usar solo ili2pg 5.5.1 e ilivalidator 1.15.0, fijados en `core/paths.py`. Al importar se
advierte si el esquema fue creado con otra versión mayor (`ch.ehi.ili2db.sender` en
`t_ili2db_settings`).

**Consecuencias.** Los esquemas viejos de `sinic_ladm` (4.4.3) deben recrearse para usarse con la 3.0.

## D04 - Dos modos de almacenamiento

**Contexto.** A veces se trabaja cada municipio por separado; otras se necesitan consultas
departamentales.

**Decisión.** Soportar ambos (`core/naming.StorageMode`):
- `PER_MUNICIPALITY`: un esquema por municipio, `<prefijo><DIVIPOLA>`.
- `SHARED`: un esquema único con un dataset por municipio.

El usuario elige en cada paso.

**Alternativas.** Imponer uno solo; se descartó a pedido del usuario.

**Consecuencias.** Crear, importar y exportar tienen ramas por modo. En el modo `SHARED` el esquema exige
columna de basket.

## D05 - La importación no crea esquemas

**Contexto.** ili2pg puede crear tablas al importar (`--doSchemaImport`), pero eso mezcla
responsabilidades y puede crear esquemas con opciones no controladas.

**Decisión.** El flujo es validar → crear → importar → exportar. La importación solo verifica que el
esquema exista, sea ili2db y sea compatible; si no, bloquea el archivo y remite al paso 2.

**Consecuencias.** Un esquema inexistente da un mensaje claro en lugar de una creación implícita.

## D06 - Políticas ante datos existentes

**Contexto.** Al reimportar un municipio hay que decidir qué pasa con lo cargado. Comportamiento de
ili2db verificado:
- `--import --dataset X` falla si X existe.
- `--replace` exige columna de basket y es transaccional.

**Decisión.** Cuatro políticas (`ImportMode`), elegidas por el usuario:

| Política | Implementación |
|----------|----------------|
| Reemplazar | `--replace --dataset <código>`. En el modo por municipio, antes se eliminan con `--delete` los demás datasets del esquema, para que quede solo el municipio actual. |
| Agregar | `--import` con un dataset nuevo `<código>_2`, `_3`, ... Si el esquema no tiene columna de basket, `--import` sin dataset. |
| Cancelar | No importa ese archivo. |
| Preguntar | Diálogo por archivo, con "aplicar a los demás". |

**Alternativas.** `--update` (sincronización por OID): no se ofreció por ahora.

**Consecuencias.** "Agregar" falla si el archivo repite objetos con restricciones UNIQUE, por ejemplo
`codigo_homologado`; es el comportamiento esperado. El reemplazo de un dataset es atómico, pero el
borrado previo de *otros* datasets (modo por municipio) se hace en llamadas separadas.

## D07 - Dataset = código DIVIPOLA y prefijo configurable

**Decisión.** El código se detecta con la expresión regular de 5 dígitos aislados, buscando en el nombre
del archivo, el ZIP de origen y hasta tres carpetas superiores (`code_from_path`). El dataset es ese
código. El prefijo del esquema (por defecto `cun`) es configurable. En la versión 2.0 estaba fijo, junto
con un sufijo `_mi` que ya no se usa.

**Consecuencias.** Si el nombre no tiene el código, el archivo queda bloqueado hasta que el usuario
escribe el esquema en el plan.

## D08 - Columna de basket obligatoria en la práctica

**Contexto.** Verificado: ili2pg responde `Model ... requires column T_basket` para
`Modelo_Aplicacion_LADMCOL_SINIC_V1_0` y `Modelo_Interno_ACC_V3` si falta `--createBasketCol`.

**Decisión.** `createBasketCol` y `createDatasetCol` vienen activos por defecto. La interfaz advierte si se
desactivan. La detección se hace con `ch.ehi.ili2db.BasketHandling=readWrite`.

## D09 - Pasar todos los modelos con contenido a `--models`

**Contexto.** Verificado: con `--models Submodelo_Cartografia_Catastral_V1_1` (solo el modelo "hoja"),
ili2pg registra los 4 modelos pero crea tablas solo para los TOPIC de ese modelo: 27 tablas en lugar de
90. La importación falla después con "no existe la relación".

**Decisión.** `suggested_models` devuelve todos los modelos excepto los `TYPE`/`REFSYSTEM`. El análisis
de importación bloquea si hay clases del XTF sin tabla (`t_ili2db_classname`).

## D10 - Contraseñas en keyring y `--dbpwd`

**Contexto.** La 2.0 guardaba contraseñas en texto plano en los perfiles. Verificado: ili2pg 5.5.1
**ignora** la contraseña de `--dbparams` y de `PGPASSFILE`; solo acepta `--dbpwd`.

**Decisión.** Las contraseñas se guardan en el Administrador de credenciales de Windows (`keyring`,
servicio `LADMAdmin`), o solo en memoria si el usuario no marca *Recordar*. Se pasan con `--dbpwd` y se
enmascaran en pantalla y logs (`mask_command`).

**Consecuencias (limitación aceptada).** Mientras corre Java, la contraseña es visible en la línea de
comandos del proceso para el mismo usuario o un administrador.

## D11 - Recrear con respaldo y restauración

**Contexto.** En la 2.0, "Recrear" hacía `DROP SCHEMA` y luego ili2pg. Si ili2pg fallaba, se perdía el
esquema. Verificado en pruebas.

**Decisión.** El esquema se renombra como `<esquema>__respaldo_<fecha>` antes de crear. Si la creación
termina bien, el respaldo se elimina; si falla o se cancela, se restaura.

## D12 - Ejecutar Java sin shell

**Contexto.** En la 2.0, `shell=True` hacía que *Detener* matara `cmd.exe` pero no Java, y las
contraseñas con `& ^ %` rompían el comando.

**Decisión.** `subprocess.Popen` con lista de argumentos, sin shell y con `CREATE_NO_WINDOW`.
`CancelToken.cancel()` mata el proceso Java. Las líneas se clasifican por prefijo (`Error:`, `Warning:`),
no por contener la palabra "error". Del error se muestra la causa de PostgreSQL cuando existe
(`ToolResult.main_error`).

## D13 - Análisis previo y verificación de conteos

**Decisión.** Antes de importar, `analyze_import` lee cabeceras y conteos del XTF en streaming e
inspecciona la base sin escribir. Clasifica cada archivo como `READY`, `CONFLICT` o `BLOCKED`. Después
de importar, compara objetos por clase del XTF con registros por tabla, filtrando por dataset.

**Consecuencias.** Las diferencias de conteo dejan el resultado *Con advertencias*, no *Error*. Las
estructuras (elementos estructurados) no se comparan.

## D14 - Herramientas descargadas con huella fija

**Contexto.** Los JAR (35 MB) no deben ir en el repositorio, pero quien clone debe poder usarlos.

**Decisión.** `core/tools_setup.py` descarga los ZIP oficiales de `downloads.interlis.ch`, verifica su
SHA-256 (fijada en el código), los extrae de forma atómica y protege contra rutas peligrosas. Se ejecuta
desde el `.bat`, el botón de *Inicio* o `python -m ladm_admin herramientas`.

**Consecuencias.** Para actualizar una versión hay que cambiar versión, URL y huella. Los ZIP oficiales
se verificaron idénticos a los que ya se usaban.

## D15 - Sin prevalidación de reglas SINIC

**Contexto.** Los logs `PROC_NOV` del IGAC rechazan entregas por reglas de negocio que ilivalidator no
revisa, por ejemplo "interesado no asociado a ningún derecho".

**Decisión.** No implementarla por ahora, por decisión del usuario.

**Consecuencias.** Un XTF válido para INTERLIS puede ser rechazado por el IGAC. Es candidata a una versión
futura (ver [estado de la implementación](estado_implementacion.md)).

## D16 - Retiro de la versión 2.0 y estructura del repositorio

**Decisión.**
- Se eliminaron `interfaz_ili2pg.py`, `creacion_modelos_fisicos.py`, `config.json*` y sus `.bat`; quedan
  en la etiqueta `v2.0`.
- Se mantiene la carpeta `windows_version/`; no se movió a la raíz, a pedido del usuario.
- Hay un solo `.gitignore` en la raíz y `.gitattributes`, que fuerza CRLF en `.bat` porque cmd.exe falla
  con LF en `goto`.

## D17 - Exportación con los modelos del esquema

**Decisión.** Al exportar por esquema se pasan a `--models` los modelos registrados en `t_ili2db_model`
del propio esquema, no los de la carpeta. En el modo `SHARED` se exporta por `--dataset`. Se exportan los
TID originales (`--exportTid`) por defecto. El log se llama `<código>_exportacion.log`; en la 2.0 era
`<código>.txt`.

## D18 - Validación con modelos de la cabecera y reporte CSV

**Decisión.** ilivalidator toma los modelos de la cabecera del XTF; no se fuerza `--models`. Se genera
siempre `--csvlog` para mostrar los errores en una tabla filtrable. Los reportes van junto al XTF o, si
venía en un ZIP, junto al ZIP. `--allObjectsAccessible` es opcional y viene desactivado, para no cambiar
los resultados respecto a la 2.0.

## D19 - Idioma y convenciones de texto

**Decisión.**
- La interfaz y los mensajes van en español con tildes.
- Los **identificadores técnicos** van en ASCII: opciones del CLI, `objectName` de Qt, claves de
  configuración, nombres de archivos y carpetas que genera la herramienta (`_validacion.log`,
  `crear_esquema/`).

**Contexto.** Un barrido automático de tildes cambió `--conexion` y el selector `#Version`, lo que rompió
el CLI y la hoja de estilos. `tests/test_cli.py` verifica que las opciones sean ASCII y que coincidan con
las documentadas.

## D20 - Datos y modelo interno fuera del repositorio

**Decisión.** No se versionan:
- `*.xtf` y `windows_version/xtf/`, que contienen datos personales de interesados;
- los logs;
- los ZIP;
- `ili2pg/`;
- `modelo_acc_interno/`, que es interno de la ACC;
- `ubuntu_version/`.

Solo se incluyen los modelos SINIC públicos y el script CTM12.

## D21 - Los archivos bloqueados se reportan como error

**Contexto.** La interfaz enviaba al proceso solo los archivos importables. Los bloqueados desaparecían de
los resultados y el resumen decía "2 correcto" sin rastro del omitido.

**Decisión.** Todos los archivos marcados se envían a `run_import`. Los bloqueados quedan como **Error**
con su motivo, igual que en el CLI, donde además afectan el código de salida.
