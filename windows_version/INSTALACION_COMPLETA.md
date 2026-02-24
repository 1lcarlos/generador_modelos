# GUIA DE INSTALACION COMPLETA
# Creacion de Modelos Fisicos LADM-COL - Windows

## ============================================
## REQUISITOS DEL SISTEMA
## ============================================

- Windows 10/11 (64-bit)
- Acceso de administrador
- Minimo 4GB RAM
- Minimo 20GB disco libre
- Conexion a internet (para descargas)

## ============================================
## PASO 1: INSTALAR POSTGRESQL 12+ CON POSTGIS
## ============================================

### 1.1 Descargar PostgreSQL

1. Ir a: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Descargar la version 12 o superior para Windows x86-64
3. Ejecutar el instalador

### 1.2 Instalar PostgreSQL

Durante la instalacion:
1. Seleccionar todos los componentes
2. Definir directorio de datos (o usar default)
3. Establecer password para usuario postgres
4. Puerto por defecto: 5432
5. Locale: Spanish, Spain (o default)
6. **IMPORTANTE**: Marcar "Launch Stack Builder" al finalizar

### 1.3 Instalar PostGIS con Stack Builder

1. En Stack Builder, seleccionar tu instalacion de PostgreSQL
2. Expandir "Spatial Extensions"
3. Seleccionar PostGIS 3.x Bundle
4. Seguir el asistente de instalacion
5. Marcar "Create spatial database" (opcional)

### 1.4 Verificar instalacion

Abrir Command Prompt o PowerShell:

```cmd
REM Verificar PostgreSQL
psql --version

REM Conectar a PostgreSQL
psql -h localhost -U postgres -d postgres

REM Dentro de psql, verificar PostGIS
SELECT PostGIS_version();

REM Salir
\q
```

### 1.5 Agregar PostgreSQL al PATH (si no se hizo automaticamente)

1. Abrir "Panel de Control" > "Sistema" > "Configuracion avanzada del sistema"
2. Click en "Variables de entorno"
3. En "Variables del sistema", seleccionar "Path" y click "Editar"
4. Agregar: `C:\Program Files\PostgreSQL\12\bin` (ajustar segun version)
5. Click "Aceptar" en todas las ventanas

## ============================================
## PASO 2: INSTALAR JAVA 8 (JRE 1.8.0)
## ============================================

### 2.1 Opcion A: Oracle Java 8 (Recomendada)

1. Ir a: https://www.oracle.com/java/technologies/javase/javase8-archive-downloads.html
2. Buscar: "Java SE Runtime Environment 8u221" (o version mas reciente de Java 8)
3. Descargar: `jre-8uXXX-windows-x64.exe`
4. Ejecutar el instalador
5. Seguir instrucciones por defecto

### 2.2 Opcion B: OpenJDK 8 (Alternativa gratuita)

1. Ir a: https://adoptium.net/
2. Seleccionar "Temurin 8 (LTS)"
3. Descargar para Windows x64
4. Ejecutar el instalador
5. **IMPORTANTE**: Marcar "Set JAVA_HOME variable"
6. Marcar "Add to PATH"

### 2.3 Verificar instalacion de Java

```cmd
REM Abrir nuevo Command Prompt (para cargar PATH actualizado)
java -version

REM Resultado esperado:
REM java version "1.8.0_XXX"
REM o
REM openjdk version "1.8.0_XXX"
```

### 2.4 Configurar JAVA_HOME (si no se hizo automaticamente)

1. Abrir "Variables de entorno" (ver paso 1.5)
2. En "Variables del sistema", click "Nueva"
3. Nombre: `JAVA_HOME`
4. Valor: `C:\Program Files\Java\jre1.8.0_XXX` (ajustar segun instalacion)
5. Editar "Path" y agregar: `%JAVA_HOME%\bin`
6. Aceptar todo

## ============================================
## PASO 3: INSTALAR PYTHON Y DEPENDENCIAS
## ============================================

### 3.1 Instalar Python 3

1. Ir a: https://www.python.org/downloads/
2. Descargar Python 3.9 o superior
3. Ejecutar instalador
4. **IMPORTANTE**: Marcar "Add Python to PATH"
5. Seleccionar "Install Now" o personalizar instalacion

### 3.2 Verificar Python

```cmd
REM Verificar Python
python --version

REM Verificar pip
pip --version
```

### 3.3 Instalar libreria psycopg2

```cmd
pip install psycopg2-binary
```

### 3.4 Verificar instalacion

```cmd
python -c "import psycopg2; print('psycopg2 OK')"
```

## ============================================
## PASO 4: CONFIGURAR EL SCRIPT
## ============================================

### 4.1 Ubicar archivos

Los archivos deben estar en:
```
C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version\
    creacion_modelos_fisicos.py
    config.json
    ejecutar_creacion.bat
    ili2pg\
        ili2pg-4.4.3.jar
        libs\
    ctm12\
        insert_ctm12_pg.sql
    modelo_acc_interno\
        *.ili
    log\
```

### 4.2 Editar configuracion

Abrir config.json con un editor de texto:

```cmd
notepad config.json
```

Modificar segun tu entorno:

```json
{
    "database": {
        "host": "localhost",
        "port": "5432",
        "database": "interno_v3_acc",
        "user": "postgres",
        "password": "TU_PASSWORD_REAL"    <-- CAMBIAR
    },
    "schemas": [
        "cun25019",
        "cun25035"
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

**IMPORTANTE**: En Windows, las rutas usan doble backslash `\\`

### 4.3 Verificar estructura de archivos

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
dir

REM Verificar JAR
dir ili2pg\ili2pg-4.4.3.jar

REM Verificar modelos
dir modelo_acc_interno\*.ili
```

## ============================================
## PASO 5: VERIFICACION PREVIA
## ============================================

### 5.1 Verificar Java con JAR

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
java -jar ili2pg\ili2pg-4.4.3.jar --version
```

### 5.2 Verificar conexion PostgreSQL

```cmd
psql -h localhost -U postgres -d postgres -c "SELECT version();"
```

### 5.3 Verificar Python

```cmd
python -c "import psycopg2, json, logging; print('Todas las librerias OK')"
```

## ============================================
## PASO 6: PRIMERA EJECUCION
## ============================================

### 6.1 Ejecutar script

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
python creacion_modelos_fisicos.py
```

### 6.2 Monitorear ejecucion

En PowerShell (otra ventana):

```powershell
Get-Content log\creacion_modelos_*.log -Wait -Tail 50
```

### 6.3 Verificar resultados

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "\dn"
```

## ============================================
## PASO 7: AUTOMATIZACION CON TAREA PROGRAMADA
## ============================================

### 7.1 Abrir Programador de tareas

```cmd
taskschd.msc
```

### 7.2 Crear tarea basica

1. Click "Crear tarea basica..."
2. Nombre: "Creacion Modelos LADM-COL"
3. Descripcion: "Ejecuta creacion automatica de modelos LADM-COL"
4. Click "Siguiente"

### 7.3 Configurar desencadenador

1. Seleccionar "Diariamente" (o la frecuencia deseada)
2. Hora: 02:00:00 (2 AM)
3. Click "Siguiente"

### 7.4 Configurar accion

1. Accion: "Iniciar un programa"
2. Programa: `C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version\ejecutar_creacion.bat`
3. Iniciar en: `C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version`
4. Click "Siguiente"

### 7.5 Finalizar

1. Marcar "Abrir dialogo de propiedades..."
2. Click "Finalizar"

### 7.6 Configurar propiedades avanzadas

En la ventana de propiedades:
1. Marcar "Ejecutar tanto si el usuario inicio sesion como si no"
2. Marcar "Ejecutar con los privilegios mas altos"
3. Configurar usuario con permisos adecuados
4. Click "Aceptar"

### 7.7 Probar tarea

1. Click derecho en la tarea
2. Seleccionar "Ejecutar"
3. Verificar en carpeta log\

## ============================================
## PASO 8: BACKUP DE BASE DE DATOS
## ============================================

### 8.1 Backup manual

```cmd
REM Crear directorio de backups
mkdir C:\backup\postgresql

REM Backup completo
pg_dump -h localhost -U postgres -Fc interno_v3_acc > C:\backup\postgresql\interno_v3_acc_%date:~6,4%%date:~3,2%%date:~0,2%.dump
```

### 8.2 Backup de un esquema

```cmd
pg_dump -h localhost -U postgres -Fc -n cun25019 interno_v3_acc > C:\backup\postgresql\cun25019_%date:~6,4%%date:~3,2%%date:~0,2%.dump
```

### 8.3 Restaurar backup

```cmd
pg_restore -h localhost -U postgres -d interno_v3_acc C:\backup\postgresql\interno_v3_acc_20251124.dump
```

### 8.4 Automatizar backups

Crear tarea programada adicional para backups (ver Paso 7).

## ============================================
## SOLUCION DE PROBLEMAS
## ============================================

### Error: "java: no se reconoce como comando"

```cmd
REM Verificar instalacion de Java
where java

REM Si no se encuentra, verificar PATH
echo %PATH%

REM Agregar Java al PATH manualmente o reinstalar Java
```

### Error: "No module named 'psycopg2'"

```cmd
pip install psycopg2-binary
```

### Error: "psql: no se reconoce como comando"

```cmd
REM Agregar PostgreSQL\bin al PATH
REM O usar ruta completa:
"C:\Program Files\PostgreSQL\12\bin\psql.exe" -h localhost -U postgres
```

### Error: conexion rechazada a PostgreSQL

```cmd
REM Verificar servicio
services.msc

REM Buscar "postgresql-x64-12" y verificar que este "Ejecutandose"
REM Si no, iniciar el servicio
```

### Error: permission denied

1. Ejecutar Command Prompt como Administrador
2. Verificar permisos de carpeta
3. Verificar usuario de Windows tiene permisos

### ili2pg timeout

Editar creacion_modelos_fisicos.py y buscar:
```python
timeout=600
```
Cambiar a:
```python
timeout=1800  # 30 minutos
```

## ============================================
## ESTRUCTURA FINAL DE DIRECTORIOS
## ============================================

```
C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version\
    creacion_modelos_fisicos.py      <-- Script principal
    config.json                       <-- Configuracion
    ejecutar_creacion.bat             <-- Wrapper para automatizacion
    README_PRINCIPAL.md               <-- Documentacion principal
    INSTALACION_COMPLETA.md           <-- Esta guia
    CHECKLIST_VALIDACION.md           <-- Lista de verificacion
    EJEMPLOS_DE_USO.md                <-- Ejemplos practicos
    RESUMEN_EJECUTIVO.md              <-- Resumen del proyecto
    ili2pg\
        ili2pg-4.4.3.jar
        libs\
            *.jar
        docs\
    ctm12\
        insert_ctm12_pg.sql
    modelo_acc_interno\
        INTERLIS_TOPOLOGY.ili
        ISO19107_PLANAS_V3_1.ili
        LADM_COL_v_4_0_1_Nucleo.ili
        Modelo_Interno_ACC_V3.ili
        Submodelo_Cartografia_Catastral_V1_1.ili
        Submodelo_Valoracion_Masiva_V1_0.ili
    log\
        creacion_modelos_*.log
        ili2pg_*.log
        ejecucion_*.log
```

## ============================================
## CONTACTO Y SOPORTE
## ============================================

### Documentacion:
- PostgreSQL: https://www.postgresql.org/docs/
- PostGIS: https://postgis.net/documentation/
- ili2pg: https://github.com/claeis/ili2db
- LADM-COL: https://github.com/AgenciaImplementacion/Asistente-LADM-COL

### Equipo ACC:
- DBA Team: Problemas de PostgreSQL
- Desarrollo GIS: Problemas de ili2pg/INTERLIS
- Area de Desarrollo: Problemas del script Python
- Infraestructura: Problemas del servidor

---

**Version:** 2.0
**Fecha:** 2025-11-24
**Plataforma:** Windows
