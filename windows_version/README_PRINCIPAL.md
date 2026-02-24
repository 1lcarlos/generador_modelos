# CREACION DE MODELOS FISICOS LADM-COL
# Agencia Catastral de Cundinamarca (ACC)
# Version Windows

## CONTENIDO DEL PAQUETE

Este paquete contiene todo lo necesario para implementar el sistema de creacion automatica de modelos fisicos LADM-COL en Windows.

### Archivos incluidos:

1. **creacion_modelos_fisicos.py** (Script principal)
   - Sistema completo de creacion de modelos
   - Gestion automatica de base de datos
   - Validacion completa de estructura
   - Logging detallado
   - Manejo robusto de errores

2. **config.json** (Configuracion)
   - Credenciales de base de datos
   - Lista de esquemas municipales
   - Rutas de archivos
   - Opciones de ili2pg

3. **ejecutar_creacion.bat** (Script de ejecucion)
   - Script wrapper para Windows
   - Verificaciones previas
   - Logging de ejecucion

4. **Documentacion completa**
   - INSTALACION_COMPLETA.md
   - CHECKLIST_VALIDACION.md
   - EJEMPLOS_DE_USO.md
   - RESUMEN_EJECUTIVO.md

---

## OBJETIVO DEL SISTEMA

Crear y mantener modelos fisicos de bases de datos PostgreSQL/PostGIS basados en archivos INTERLIS (.ili) bajo el estandar LADM-COL, de forma **automatica y recurrente**.

### Caracteristicas principales:

- Creacion automatica de base de datos si no existe
- Habilitacion automatica de PostGIS y uuid-ossp
- Proceso idempotente (puede ejecutarse multiples veces)
- Configuracion externa via archivo JSON
- Logging completo de todas las operaciones
- Validacion exhaustiva de estructura creada
- Metricas de rendimiento por esquema
- Ejecutable manualmente o por tarea programada
- Manejo robusto de errores con logs detallados

---

## INICIO RAPIDO (5 PASOS)

### 1. Instalar PostgreSQL 12+ con PostGIS

Descargar desde: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

Durante la instalacion:
- Marcar "Stack Builder" para instalar PostGIS
- O instalar PostGIS despues desde Stack Builder

### 2. Instalar Java 8

Descargar desde: https://www.oracle.com/java/technologies/javase/javase8-archive-downloads.html

O usar OpenJDK 8: https://adoptium.net/

Agregar Java al PATH del sistema.

### 3. Instalar Python 3 y dependencias

Descargar desde: https://www.python.org/downloads/

Luego instalar psycopg2:
```cmd
pip install psycopg2-binary
```

### 4. Configurar archivos

```cmd
REM Editar config.json con tus credenciales
notepad config.json

REM Cambiar:
REM - password
REM - verificar puerto (5432 por defecto en Windows)
REM - ajustar base_dir si es necesario
```

### 5. Ejecutar

```cmd
REM Opcion 1: Ejecutar script directamente
python creacion_modelos_fisicos.py

REM Opcion 2: Usar el script batch
ejecutar_creacion.bat
```

**Listo!** El sistema creara la base de datos, habilitara extensiones, y generara todos los esquemas automaticamente.

---

## CONFIGURACION DETALLADA

### Estructura del config.json

```json
{
    "database": {
        "host": "localhost",
        "port": "5432",
        "database": "interno_v3_acc",
        "user": "postgres",
        "password": "TU_PASSWORD_AQUI"   <-- CAMBIAR
    },
    "schemas": [
        "cun25019",
        "cun25035",
        "cun25436",
        "cun25040",
        "cun25053",
        "cun25095"
    ],
    "paths": {
        "base_dir": "C:\\ladm_col\\desarrollos\\creacion_modelos_fisicos\\windows_version",
        "jar": "ili2pg\\ili2pg-4.4.3.jar",
        "ctm12": "ctm12\\insert_ctm12_pg.sql",
        "model": "modelo_acc_interno\\Modelo_Interno_ACC_V3.ili",
        "log_dir": "log"
    }
}
```

### Personalizacion de esquemas

Para agregar/modificar municipios, edita la lista `schemas`:

```json
"schemas": [
    "cun25001",
    "cun25019",
    "cun25035"
]
```

El script procesara todos los esquemas de la lista automaticamente.

---

## QUE HACE EL SCRIPT

### Flujo de ejecucion:

```
1. Cargar configuracion desde config.json
2. Conectar a PostgreSQL
3. Crear base de datos "interno_v3_acc" (si no existe)
4. Habilitar extensiones PostGIS y uuid-ossp
5. Validar prerequisitos (Java, JAR, modelos ILI)
6. Para cada esquema en la lista:
   a. Eliminar esquema existente (si recreate=True)
   b. Ejecutar ili2pg con modelo INTERLIS
   c. Validar estructura creada
   d. Registrar metricas
7. Generar resumen de ejecucion
8. Cerrar conexiones
```

### Lo que crea por cada esquema:

- Esquema principal: `cun25019`
- Esquema de metadatos: `cun25019_mi`
- ~100-150 tablas segun modelo LADM-COL
- Tablas de dominio (terminan en 'tipo')
- Constraints (foreign keys, checks, etc.)
- Indices espaciales (GIST para geometrias)
- Triggers y funciones
- Metadatos ili2db completos

---

## VALIDACION AUTOMATICA

El script valida automaticamente:

```
- Esquema existe
- Numero de tablas creadas
- Constraints configurados
- Indices totales
- Indices espaciales (GIST)
- Tablas de dominio presentes
- Esquema de metadatos (_mi) existe
```

Ejemplo de salida:

```
[VALIDACION] Estructura - Esquema: cun25019
------------------------------------------------------------
  Esquema existe: OK
  Tablas creadas: 142
  Constraints: 356
  Indices totales: 278
  Indices espaciales: 45
  Tablas de dominio: 28
  Metadatos ili2db: OK
------------------------------------------------------------
```

---

## SISTEMA DE LOGS

### Tipos de logs generados:

1. **Log principal** del script:
   ```
   log\creacion_modelos_20251124_143022.log
   ```

2. **Logs de ili2pg** (uno por esquema):
   ```
   log\ili2pg_cun25019_20251124_143025.log
   ```

3. **Log de ejecucion wrapper** (si usas el .bat):
   ```
   log\ejecucion_20251124_143000.log
   ```

### Ver logs:

```cmd
REM Ver ultimo log
type log\creacion_modelos_*.log

REM Ver en tiempo real (PowerShell)
Get-Content log\creacion_modelos_*.log -Wait
```

---

## AUTOMATIZACION CON TAREAS PROGRAMADAS

### Configurar tarea programada en Windows:

1. Abrir "Programador de tareas" (taskschd.msc)
2. Crear tarea basica
3. Configurar:
   - Nombre: "Creacion Modelos LADM-COL"
   - Desencadenador: Diariamente a las 2:00 AM
   - Accion: Iniciar programa
   - Programa: `C:\...\windows_version\ejecutar_creacion.bat`

---

## IMPORTANTE: JAVA 8

### Por que Java 8 especificamente?

ili2pg 4.4.3 fue compilado y probado con Java 8. **Java 8 es la version mas estable** segun pruebas del equipo ACC.

### Opciones de instalacion:

**Opcion 1: Oracle Java 8** (Recomendada para maxima estabilidad)
- Descargar desde Oracle
- Requiere cuenta gratuita

**Opcion 2: OpenJDK 8** (Mas facil)
- Descargar desde Adoptium
- https://adoptium.net/

---

## COMANDOS UTILES

### Verificar estado con psql:

```cmd
REM Ver esquemas creados
psql -h localhost -U postgres -d interno_v3_acc -c "\dn"

REM Ver tablas de un esquema
psql -h localhost -U postgres -d interno_v3_acc -c "\dt cun25019.*"
```

### Backup:

```cmd
pg_dump -h localhost -U postgres -Fc interno_v3_acc > interno_v3_acc_%date:~6,4%%date:~3,2%%date:~0,2%.dump
```

---

## SOLUCION DE PROBLEMAS

### Error: "java: no se reconoce como comando"
```cmd
REM Verificar Java en PATH
java -version

REM Si no funciona, agregar Java al PATH:
REM Panel de Control > Sistema > Configuracion avanzada > Variables de entorno
REM Agregar ruta de Java\bin al PATH
```

### Error: "No module named 'psycopg2'"
```cmd
pip install psycopg2-binary
```

### Ver logs detallados:
```cmd
type log\creacion_modelos_*.log
```

---

## CHECKLIST RAPIDO

- [ ] PostgreSQL 12+ instalado con PostGIS
- [ ] Java 8 instalado y en PATH
- [ ] Python 3 instalado
- [ ] psycopg2-binary instalado
- [ ] Archivos en el directorio correcto
- [ ] config.json editado con credenciales correctas
- [ ] Prueba manual exitosa

---

**Version:** 2.0
**Fecha:** 2025-11-24
**Autor:** ACC - Area de Desarrollo
**Plataforma:** Windows
