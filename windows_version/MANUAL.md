# Manual - Administrador de Modelos LADM

**Agencia Catastral de Cundinamarca (ACC)**
**Version 2.0 - 2025**

---

## 1. Introduccion

El **Administrador de Modelos LADM** es una herramienta para gestionar esquemas LADM-COL en bases de datos PostgreSQL/PostGIS. Permite:

- **Crear esquemas** a partir de modelos INTERLIS (.ili) usando ili2pg
- **Exportar datos** de esquemas existentes a archivos XTF
- **Validar archivos XTF** contra modelos INTERLIS usando ilivalidator

Esta dirigida a equipos tecnicos de entidades territoriales que trabajan con el estandar LADM-COL para gestion catastral.

---

## 2. Requisitos e Instalacion

### Requisitos

| Componente | Version minima |
|------------|---------------|
| Windows | 10/11 (64-bit) |
| Python | 3.8+ |
| Java | JRE 1.8.0 (Java 8) |
| PostgreSQL | 12+ con PostGIS |

### Pasos de instalacion

1. **Instalar Python** desde https://www.python.org/downloads/
   - Marcar "Add Python to PATH" durante la instalacion

2. **Instalar Java 8** (JRE o JDK) desde https://www.java.com/

3. **Instalar PostgreSQL** con la extension PostGIS

4. **Instalar dependencia Python**:
   ```cmd
   pip install psycopg2-binary
   ```

5. **Descomprimir** el paquete del administrador en una carpeta local

6. **Ejecutar**:
   ```cmd
   ejecutar_interfaz.bat
   ```

---

## 3. Configuracion

### Perfiles

La aplicacion permite guardar y cargar **perfiles de configuracion** para reutilizar ajustes entre sesiones. Los perfiles almacenan todas las configuraciones de todas las pestanas.

- **Guardar**: Almacena la configuracion actual con un nombre
- **Guardar Como...**: Crea un nuevo perfil
- **Cargar**: Restaura un perfil previamente guardado
- **Eliminar**: Borra un perfil

La ultima configuracion usada se restaura automaticamente al abrir la aplicacion.

### Rutas de archivos

| Campo | Descripcion |
|-------|-------------|
| Archivo ili2pg.jar | Ruta al JAR de ili2pg (incluido en `ili2pg/`) |
| Script CTM12 (SQL) | Script SQL para insertar CTM12 (`ctm12/insert_ctm12_pg.sql`) |
| Carpeta de modelos | Carpeta que contiene los archivos .ili |
| Carpeta de logs | Donde se guardan los logs de ejecucion |

### Base de datos

| Campo | Valor tipico |
|-------|-------------|
| Host | localhost |
| Puerto | 5432 |
| Base de datos | nombre_bd |
| Usuario | postgres |
| Password | (su password) |

Use el boton **Probar Conexion** para verificar la conectividad antes de ejecutar.

### Opciones ili2pg

En el panel derecho de la pestana "Configuracion" se encuentran las opciones de ili2pg. Estas permiten habilitar/deshabilitar funcionalidades del motor. Las opciones por defecto son las recomendadas para LADM-COL. Opciones principales:

- **setupPgExt**: Configurar extensiones PostgreSQL
- **coalesceCatalogueRef**: Unir referencias de catalogo
- **createEnumTabs**: Crear tablas de enumeracion
- **smart2Inheritance**: Herencia inteligente tipo 2
- **strokeArcs**: Convertir arcos a segmentos
- **createDatasetCol**: Crear columna de dataset
- **createBasketCol**: Crear columna de basket
- **defaultSrsCode**: 9377 (MAGNA-SIRGAS / CTM12)

Se pueden seleccionar/deseleccionar todas o restaurar los valores predeterminados con los botones rapidos.

---

## 4. Modulo: Crear Esquemas

Este modulo crea esquemas en PostgreSQL a partir de modelos INTERLIS.

### Flujo de trabajo

1. En la pestana **Configuracion**:
   - En el panel izquierdo: seleccione rutas, modelos, conexion BD, esquemas y SRS
   - En el panel derecho: revise las opciones ili2pg habilitadas (las predeterminadas suelen ser correctas)
   - Opcionalmente configure el script CTM12

2. En la pestana **Crear Esquemas**:
   - Use **Actualizar Vista Previa** para ver el comando que se ejecutara
   - Presione **EJECUTAR** para iniciar la creacion
   - Si un esquema ya existe, se le preguntara si desea recrear, actualizar u omitir
   - Monitoree el progreso en el log en tiempo real

### Esquemas existentes

Cuando un esquema ya existe en la base de datos, la aplicacion ofrece tres opciones:

- **RECREAR**: Elimina el esquema existente y lo crea de nuevo
- **ACTUALIZAR**: Ejecuta ili2pg sobre el esquema existente (agrega modelos)
- **OMITIR**: No procesa ese esquema

Se puede marcar "Aplicar esta decision a todos" para no preguntar por cada esquema.

---

## 5. Modulo: Exportar XTF

Este modulo exporta datos de esquemas PostgreSQL a archivos XTF (formato de transferencia INTERLIS).

### Configuracion

1. En la pestana **Exportar XTF**:
   - Seleccione la ruta al JAR de ili2pg (puede ser diferente al de creacion)
   - Opcionalmente seleccione la carpeta de modelos (modeldir)
   - Seleccione la carpeta de salida donde se crearan los archivos
   - Ingrese el nombre del modelo (ej: `Modelo_Aplicacion_LADMCOL_SINIC_V1_0`)
   - Configure la conexion a la base de datos

### Deteccion de esquemas

- Presione **Detectar Esquemas (cun*)** para buscar automaticamente esquemas que empiecen con "cun" en la base de datos
- Seleccione los esquemas que desea exportar (Ctrl+Click para seleccion multiple)

### Ejecucion

- Presione **EXPORTAR XTF** para iniciar
- Para cada esquema se crea una subcarpeta con el numero del esquema (ej: `25019/`)
- Dentro de cada subcarpeta se genera:
  - `{numero}.xtf` - Archivo de datos
  - `{numero}.txt` - Log de la exportacion

---

## 6. Modulo: Validar XTF

Este modulo valida archivos XTF contra modelos INTERLIS usando **ilivalidator**.

### Configuracion

1. En la pestana **Validar XTF**:
   - Seleccione la ruta al JAR de ilivalidator (incluido en `ili2pg/ilivalidator-1.15.0/`)
   - Opcionalmente seleccione la carpeta de modelos (modeldir)
   - Ingrese el nombre del modelo contra el cual validar
   - Seleccione la carpeta de entrada que contiene los archivos XTF

### Escaneo de archivos

- Presione **Escanear Carpeta** para buscar recursivamente archivos .xtf en la carpeta seleccionada
- Los archivos encontrados se muestran en la lista con su ruta relativa
- Seleccione los archivos que desea validar

### Ejecucion y resultados

- Presione **VALIDAR** para iniciar la validacion
- Para cada archivo XTF se ejecuta ilivalidator
- Se genera un log de validacion junto a cada archivo: `{nombre}_validacion.log`
- El log en pantalla muestra el resultado de cada archivo (VALIDO o con ERRORES)
- Al finalizar se muestra un resumen con el conteo de archivos validos y con errores

### Ejemplo

Para un archivo `25154/25154.xtf`:
- Se genera el log: `25154/25154_validacion.log`
- El log contiene el detalle de errores y advertencias de ilivalidator

---

## 7. Uso por Linea de Comandos

Para automatizacion, se puede usar el script CLI directamente:

### Configuracion via config.json

Copie `config.json.ejemplo` a `config.json` y edite los valores:

```json
{
    "database": {
        "host": "localhost",
        "port": "5432",
        "database": "nombre_base_datos",
        "user": "postgres",
        "password": "su_password"
    },
    "schemas": ["cun25019", "cun25035"],
    "paths": {
        "base_dir": "C:\\ruta\\a\\windows_version",
        "jar": "ili2pg\\ili2pg-4.4.3.jar",
        "ctm12": "ctm12\\insert_ctm12_pg.sql",
        "model": "modelo_acc_interno\\Modelo_Interno_ACC_V3.ili",
        "log_dir": "log"
    },
    "ili2pg": {
        "srs_code": "9377",
        "options": { ... }
    }
}
```

### Ejecucion

```cmd
REM Usando el script batch
ejecutar_creacion.bat

REM O directamente
python creacion_modelos_fisicos.py
```

---

## 8. Distribucion del paquete

Para compartir esta herramienta con otras personas o entidades, basta con entregar un archivo **ZIP** con el contenido de la carpeta `windows_version/`. No se requiere instalador.

### Que incluir en el ZIP

```
administrador_modelos_ladm.zip
  └─ administrador_modelos_ladm/
       README.md
       MANUAL.md
       ejecutar_interfaz.bat
       ejecutar_creacion.bat
       config.json.ejemplo
       interfaz_ili2pg.py
       creacion_modelos_fisicos.py
       ili2pg/                        (incluir completa: JARs de ili2pg e ilivalidator)
       ctm12/                         (script insert_ctm12_pg.sql)
       modelo_acc_interno/            (archivos .ili necesarios)
```

**No incluir** en el ZIP:
- `config.json` (contiene passwords reales)
- `log/` (se genera automaticamente)
- `__pycache__/`
- `.gitignore`

### Que debe tener el destinatario (requisitos previos)

| Componente | Como verificar |
|------------|---------------|
| Windows 10/11 | - |
| Python 3.8+ | `python --version` |
| Java 8 (JRE) | `java -version` |
| PostgreSQL 12+ con PostGIS | Servicio corriendo en el equipo o accesible por red |
| psycopg2-binary | `pip install psycopg2-binary` |

### Pasos para el destinatario

1. Descomprimir el ZIP en una carpeta local (ej: `C:\herramientas\administrador_modelos_ladm\`)
2. Instalar la dependencia Python si no la tiene: `pip install psycopg2-binary`
3. Hacer doble clic en `ejecutar_interfaz.bat`
4. En la primera ejecucion, configurar las rutas y conexion a base de datos
5. Guardar la configuracion como perfil para reutilizarla

### Como generar el ZIP

Desde la carpeta del proyecto:

```cmd
REM Desde la carpeta padre de windows_version
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos

REM Crear ZIP excluyendo archivos innecesarios
powershell Compress-Archive -Path windows_version\* -DestinationPath administrador_modelos_ladm.zip
```

O simplemente: clic derecho sobre la carpeta `windows_version` > "Comprimir en archivo ZIP", y luego eliminar del ZIP los archivos `config.json`, `log/` y `__pycache__/`.

### Notas sobre actualizaciones

Para distribuir una nueva version, genere un nuevo ZIP y pidales a los destinatarios que:
1. Respalden su `config.json` si usan la linea de comandos
2. Reemplacen todos los archivos con los del nuevo ZIP
3. Los perfiles de la interfaz grafica se guardan en `%USERPROFILE%\.ili2pg_gui\` y se conservan entre versiones

---

## 9. Solucion de Problemas

### "Python no esta instalado o no esta en el PATH"
- Instale Python y asegurese de marcar "Add Python to PATH"
- Reinicie la terminal despues de instalar

### "Java no encontrado" o errores al ejecutar JAR
- Instale Java 8 (JRE 1.8.0) y asegurese de que `java` este en el PATH
- Verifique con: `java -version`

### "psycopg2 no instalado"
- Ejecute: `pip install psycopg2-binary`

### Error de conexion a PostgreSQL
- Verifique que PostgreSQL este corriendo
- Verifique host, puerto, usuario y password
- Verifique que el usuario tenga permisos de creacion de bases de datos/esquemas
- Use el boton "Probar Conexion" para diagnosticar

### "Archivo .jar no encontrado"
- Verifique que la ruta al JAR es correcta
- Los JARs se incluyen en las carpetas `ili2pg/` y `ili2pg/ilivalidator-1.15.0/`

### Error "schema already exists"
- Al recrear un esquema, seleccione la opcion "RECREAR" para eliminar el existente
- Si esta actualizando, seleccione "ACTUALIZAR"

### Errores de validacion XTF
- Revise el log de validacion generado junto al archivo .xtf
- Verifique que el nombre del modelo sea correcto
- Verifique que la carpeta de modelos (modeldir) contenga los .ili necesarios

### La interfaz no responde durante la ejecucion
- Los procesos largos se ejecutan en hilos separados, la interfaz deberia seguir respondiendo
- Si se congela, espere a que termine el proceso actual
- Use el boton DETENER para cancelar un proceso en ejecucion

---

## Estructura del paquete

```
windows_version/
    interfaz_ili2pg.py             <- Interfaz grafica (4 pestanas)
    ejecutar_interfaz.bat          <- Iniciar interfaz
    creacion_modelos_fisicos.py    <- Script CLI
    ejecutar_creacion.bat          <- Wrapper CLI
    config.json.ejemplo            <- Plantilla de configuracion CLI
    ili2pg/                        <- Herramienta ili2pg (JAR)
      ili2pg-4.4.3.jar
      ili2pg-5.5.1/
      ilivalidator-1.15.0/         <- Herramienta ilivalidator (JAR)
    ctm12/                         <- Script CTM12
      insert_ctm12_pg.sql
    modelo_acc_interno/            <- Modelos .ili de ejemplo
    log/                           <- Logs de ejecucion
```

---

**Agencia Catastral de Cundinamarca - Area de Desarrollo**
