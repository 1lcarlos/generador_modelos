# Manual - Administrador de Modelos LADM-COL 3.0

**Agencia Catastral de Cundinamarca (ACC)**

---

## 1. Introducción

La herramienta gestiona datos LADM-COL en PostgreSQL/PostGIS usando ili2pg 5.5.1 e ilivalidator 1.15.0.
Está organizada como un flujo de cuatro pasos:

| Paso | Módulo | Herramienta |
|------|--------|-------------|
| 1 | Validar XTF | ilivalidator |
| 2 | Crear esquema | ili2pg `--schemaimport` |
| 3 | Importar XTF | ili2pg `--import` / `--replace` |
| 4 | Exportar XTF | ili2pg `--export` |

En la parte superior de la ventana siempre se ve la **base de datos** y el **perfil de modelo** activos.
Todas las operaciones usan esa selección.

---

## 2. Instalación

| Componente | Versión | Verificación |
|------------|---------|--------------|
| Windows | 10/11 64-bit | - |
| Python | 3.10+ | `python --version` |
| Java | 8+ | `java -version` |
| PostgreSQL | 12+ con PostGIS | página *Inicio* > Estado del entorno |

1. Clone el repositorio o descomprima el paquete en una carpeta local.
2. Ejecute `windows_version\ejecutar_administrador.bat`. La primera vez:
   - instala `PySide6`, `psycopg2-binary` y `keyring` (`requirements.txt`);
   - descarga **ili2pg 5.5.1** e **ilivalidator 1.15.0** desde `downloads.interlis.ch` a la carpeta
     `ili2pg/`. Cada archivo se verifica con su huella SHA-256 antes de instalarlo.
3. Revise la página **Inicio**: muestra si Java, ili2pg, ilivalidator, la base de datos y el perfil de
   modelo están listos. Si faltan las herramientas, aparece el botón **Descargar herramientas**.

Sin internet: copie la carpeta `ili2pg/` desde otra instalación, o indique la ruta de los JAR en
*Configuración → Herramientas y general*.

---

## 3. Configuración

### Conexiones

Cada conexión guarda servidor, puerto, base de datos y usuario. La contraseña se guarda en el
**Administrador de credenciales de Windows** (si se marca *Recordar*); nunca se escribe en archivos.
Use **Probar conexión** para verificar el acceso y la disponibilidad de PostGIS. Si la base de datos no
existe, se crea al crear el primer esquema.

### Perfiles de modelo

Un perfil agrupa:

- **Carpeta de modelos** con los `.ili`.
- **Modelos** para los que se crean tablas. Use *Usar sugeridos*: se incluyen todos los modelos con
  contenido propio. Los modelos `TYPE` entran como dependencias.
  > ili2pg solo crea tablas para los TOPIC de los modelos indicados; si se omite un modelo, sus clases
  > quedan sin tabla y la importación se bloquea.
- **EPSG** (9377 = MAGNA-SIRGAS Origen-Nacional) y **script previo** (CTM12).
- **Opciones de ili2pg** agrupadas, con descripción en cada casilla.

La herramienta avisa si un modelo está definido en dos archivos de la carpeta.

**Importante:** los modelos SINIC e Interno ACC **exigen la opción *Columna de basket***
(`createBasketCol`). Esa opción además permite reemplazar los datos de un municipio al importar.

### Herramientas y general

- Rutas de Java, ili2pg e ilivalidator. Si se dejan vacías, se usa Java del sistema (`JAVA_HOME` o el
  `PATH`) y las versiones fijadas descargadas en `ili2pg/`.
- Memoria máxima de Java, para XTF muy grandes.
- **Prefijo de esquemas** (por defecto `cun`). En el modo "un esquema por municipio", el esquema es
  prefijo + código DIVIPOLA, por ejemplo `cun25279`.
- Carpeta de logs y tema (claro, oscuro o según el sistema).
- **Importar perfiles de la versión 2.0.** Las contraseñas que estaban en texto plano pasan al
  Administrador de credenciales.

La configuración se guarda en `%APPDATA%\LADMAdmin\settings.json`, sin contraseñas. Se conserva al
actualizar la aplicación.

---

## 4. Organización de los datos: dos modos

| Modo | Esquemas | Cuándo usarlo |
|------|----------|---------------|
| **Un esquema por municipio** | `cun25279`, `cun25436`, ... | Entregas independientes por municipio. |
| **Esquema único con datasets** | `sinic_cundinamarca` con un dataset por municipio | Consultas departamentales y menos tablas. |

En ambos modos el **dataset** de cada municipio es su código DIVIPOLA. Así se puede reemplazar un
municipio sin tocar a los demás.

---

## 5. Paso 1 - Validar XTF

1. Agregue archivos `.xtf`, `.zip` o carpetas (arrastrando o con los botones). Se buscan en subcarpetas.
   Los XTF de los ZIP se extraen en `%LOCALAPPDATA%\LADMAdmin\trabajo\` y el ZIP original no se modifica.
2. La tabla muestra el municipio detectado, los modelos de la cabecera y el tamaño.
3. Pulse **Validar archivos**.

Junto a cada archivo se generan `<nombre>_validacion.log` y `<nombre>_validacion.csv`. Si el XTF venía en
un ZIP, se generan junto al ZIP con el nombre `<zip>_<xtf>_validacion.log`. **Doble clic** sobre un
archivo abre la tabla de errores (mensaje, clase, TID, línea, coordenadas), con filtro y opción de copiar.

En *Modelos* se usa la carpeta del perfil activo u otra carpeta. ilivalidator toma los modelos de la
cabecera de cada XTF. En *Opciones avanzadas* hay dos opciones más:
- **Verificar referencias entre todos los objetos** (`--allObjectsAccessible`): reporta referencias a
  objetos que no están en el archivo.
- **Reporte en formato XTF** (`--xtflog`).

Al terminar, el botón **Ir a Importar** envía los archivos válidos al paso 3.

---

## 6. Paso 2 - Crear esquema

1. Elija el modo (sección 4).
   - **Por municipio:** escriba los códigos DIVIPOLA o los nombres de esquema, o use *Tomar municipios
     de archivos XTF*.
   - **Esquema único:** escriba el nombre del esquema.
2. **Verificar en la base de datos** muestra si cada esquema existe, con qué versión de ili2pg se creó y
   si tiene datos.
3. Revise el perfil de modelo. Si falta la columna de basket, aparece una advertencia.
4. Si el esquema ya existe: *Preguntar*, *Omitir*, *Actualizar estructura* o *Recrear*.

**Recrear es seguro:** el esquema original se renombra como respaldo y solo se elimina si la nueva
creación termina bien. Si falla, se restaura automáticamente.

La *Vista previa del comando ili2pg* muestra el comando exacto, con la contraseña oculta. Los logs quedan
en `<carpeta de logs>/crear_esquema/`.

---

## 7. Paso 3 - Importar XTF

1. **Destino:** un esquema por municipio (`cun<código>`) o un esquema único (se elige de la lista de
   esquemas ili2db de la base de datos).
2. **Archivos:** al agregarlos se analiza el plan sin escribir en la base de datos.

| Estado | Significado |
|--------|-------------|
| Listo | El esquema existe, es compatible y no tiene datos de ese municipio. |
| Ya tiene datos | Se aplicará la política de conflicto elegida. |
| Bloqueado | No se puede importar. La columna *Observaciones* explica el motivo. |

   Motivos de bloqueo:
   - El esquema no existe. Créelo en el paso 2: la importación nunca crea esquemas.
   - El XTF usa modelos que no están en el esquema; por ejemplo, un XTF del modelo Interno ACC sobre un
     esquema SINIC.
   - Hay clases del XTF sin tabla, porque el esquema se creó sin todos los modelos.
   - Dos archivos del lote apuntan al mismo esquema y dataset.

   Con doble clic se puede cambiar el esquema destino o el dataset. Las casillas excluyen archivos del
   lote, y el menú contextual muestra los objetos por clase.
3. **Si el destino ya tiene datos:**
   - *Preguntar en cada caso*: muestra un diálogo con la opción *aplicar a los demás*.
   - *Reemplazar*: ejecuta `--replace` del dataset del municipio. Es una sola transacción: si falla, los
     datos anteriores se conservan. En el modo por municipio también elimina otros datasets del esquema.
   - *Agregar como nuevo dataset*: conserva los datos actuales. Falla si el archivo repite objetos ya
     cargados (restricciones UNIQUE).
   - *No importar*: omite el archivo.
4. **Opciones avanzadas:**
   - Validar durante la importación (activada por defecto).
   - Verificar los conteos por clase después de importar.
   - Omitir errores de referencia o de geometría.

Al finalizar, cada archivo indica si se importó y si los conteos de la base de datos coinciden con el XTF.
Los logs quedan en `<carpeta de logs>/importar/`.

---

## 8. Paso 4 - Exportar XTF

1. Pulse **Cargar desde la base de datos**. En modo por municipio se listan los esquemas ili2db con el
   prefijo; en esquema único, los datasets.
2. Marque los destinos, con filtro y botones *Todos* o *Ninguno*.
3. Elija la carpeta de salida. Se crea `<salida>/<código>/<código>.xtf` y `<código>_exportacion.log`.
4. Opciones: exportar los TID originales (recomendado) y validar durante la exportación.

Al terminar, **Validar archivos exportados** los envía al paso 1.

---

## 9. Línea de comandos

```cmd
ejecutar_administrador.bat listar                 :: conexiones y perfiles guardados
ejecutar_administrador.bat herramientas           :: descarga ili2pg/ilivalidator si faltan
ejecutar_administrador.bat validar <rutas...> [--perfil P] [--modeldir D] [--modelos A;B] [--todos-accesibles]
ejecutar_administrador.bat crear --esquemas cun1,cun2 [--conexion C] [--perfil P] [--si-existe omitir|actualizar|recrear]
ejecutar_administrador.bat importar <rutas...> [--conexion C] [--perfil P] [--esquema-unico E]
        [--si-hay-datos cancelar|reemplazar|agregar] [--sin-validacion] [--solo-analizar]
ejecutar_administrador.bat exportar --salida DIR (--esquemas a,b | --todos | --esquema-unico E)
```

- Sin `--conexion` ni `--perfil` se usan los activos en la interfaz.
- `importar --solo-analizar` muestra el plan (destino y estado de cada archivo) sin importar.
- `exportar --esquema-unico E` exporta todos los datasets de ese esquema.
- La contraseña se toma del Administrador de credenciales, de la variable `LADM_PGPASSWORD` o se pide
  por consola.
- El código de salida es 1 si algún elemento falló.

---

## 10. Solución de problemas

| Mensaje | Causa y solución |
|---------|------------------|
| `Model ... requires column T_basket` | Active *Columna de basket* en el perfil y vuelva a crear el esquema. |
| Esquema "creado con ili2pg 4.x" | Recrée el esquema con la versión 5.5.1; mezclar versiones puede fallar. |
| `llave duplicada viola restricción de unicidad` al agregar | El archivo ya estaba cargado. Use *Reemplazar*. |
| `no existe la relación ...` | El esquema se creó sin todos los modelos. Use *Usar sugeridos* en el perfil y recrée el esquema. |
| No se encontró Java | Instale Java 8+ o indique su ruta en Configuración > Herramientas. |
| ili2pg / ilivalidator no encontrado | Pulse *Descargar herramientas* en Inicio o ejecute `ejecutar_administrador.bat herramientas`. |
| La huella SHA-256 no coincide | La descarga se dañó o el archivo fue alterado. Vuelva a intentarlo; no se instala nada. |
| Contraseña no guardada | Se pide al ejecutar. Marque *Recordar* para guardarla en Windows. |

**Nota de seguridad:** ili2pg solo acepta la contraseña por línea de comandos (`--dbpwd`). La herramienta
la oculta en pantalla y en los logs, pero durante la ejecución es visible para el mismo usuario en el
administrador de tareas.

---

**Agencia Catastral de Cundinamarca - Área de Desarrollo**
