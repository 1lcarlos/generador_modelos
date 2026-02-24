# EJEMPLOS DE USO
# Creacion de Modelos Fisicos LADM-COL - Windows

## ============================================
## EJEMPLO 1: PRIMERA EJECUCION
## ============================================

```cmd
REM 1. Navegar al directorio
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version

REM 2. Verificar que todo esta listo
dir

REM 3. Ejecutar el script
python creacion_modelos_fisicos.py

REM 4. Resultado esperado:
REM ======================================================================
REM CREACION DE MODELOS FISICOS LADM-COL
REM Agencia Catastral de Cundinamarca
REM Version Windows
REM ======================================================================
REM
REM Archivo de log: ...\log\creacion_modelos_20251124_143022.log
REM ...
```

## ============================================
## EJEMPLO 2: AGREGAR NUEVOS MUNICIPIOS
## ============================================

### Paso 1: Editar config.json

```cmd
notepad config.json
```

### Paso 2: Agregar codigos de municipios

```json
{
    "schemas": [
        "cun25019",
        "cun25035",
        "cun25436",
        "cun25040",
        "cun25053",
        "cun25095",
        "cun25154",
        "cun25290",
        "cun25843"
    ]
}
```

### Paso 3: Ejecutar nuevamente

```cmd
python creacion_modelos_fisicos.py
```

**Resultado:** Se crearan los nuevos esquemas sin afectar los existentes.

## ============================================
## EJEMPLO 3: MONITOREAR EJECUCION EN TIEMPO REAL
## ============================================

### Ventana 1: Ejecutar script

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
python creacion_modelos_fisicos.py
```

### Ventana 2: Ver logs en tiempo real (PowerShell)

```powershell
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
Get-Content log\creacion_modelos_*.log -Wait -Tail 50
```

### Ventana 3: Ver ultimo log (cmd)

```cmd
REM Mostrar ultimas lineas del log
for /f "delims=" %i in ('dir /b /od log\creacion_modelos_*.log') do set LASTLOG=log\%i
more +0 %LASTLOG%
```

## ============================================
## EJEMPLO 4: VALIDAR RESULTADOS
## ============================================

### Conectar a la base de datos

```cmd
psql -h localhost -U postgres -d interno_v3_acc
```

### Dentro de psql:

```sql
-- Ver todos los esquemas creados
\dn

-- Ver tablas de un esquema
\dt cun25019.*

-- Contar tablas por esquema
SELECT
    schemaname,
    COUNT(*) as total_tablas
FROM pg_tables
WHERE schemaname LIKE 'cun25%'
  AND schemaname NOT LIKE '%_mi'
GROUP BY schemaname
ORDER BY schemaname;

-- Ver indices espaciales
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE indexdef ILIKE '%USING gist%'
  AND schemaname = 'cun25019'
LIMIT 10;

-- Ver tablas de dominio
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'cun25019'
  AND table_name LIKE '%tipo'
ORDER BY table_name;

-- Salir
\q
```

## ============================================
## EJEMPLO 5: EJECUTAR CON SCRIPT BATCH
## ============================================

### Ejecucion simple

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
ejecutar_creacion.bat
```

### Resultado esperado

```
==========================================
  CREACION DE MODELOS LADM-COL
  Agencia Catastral de Cundinamarca
==========================================

[OK] Script Python encontrado
[OK] Archivo de configuracion encontrado
[OK] Java encontrado
[OK] Python encontrado

[INFO] Todos los prerequisitos verificados OK

[INFO] Ejecutando creacion_modelos_fisicos.py...

[OK] Proceso completado exitosamente

[INFO] Log completo disponible en: log\ejecucion_20251124_143000.log
```

## ============================================
## EJEMPLO 6: CONFIGURAR TAREA PROGRAMADA
## ============================================

### Usando interfaz grafica

1. Abrir Programador de tareas: `taskschd.msc`
2. "Crear tarea basica..."
3. Nombre: "Creacion Modelos LADM-COL"
4. Desencadenador: Diariamente, 02:00
5. Accion: Iniciar programa
   - Programa: `ejecutar_creacion.bat`
   - Iniciar en: `C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version`
6. Finalizar y configurar propiedades

### Usando linea de comandos

```cmd
REM Crear tarea programada
schtasks /create /tn "Creacion Modelos LADM-COL" /tr "C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version\ejecutar_creacion.bat" /sc daily /st 02:00 /ru SYSTEM

REM Verificar tarea
schtasks /query /tn "Creacion Modelos LADM-COL"

REM Ejecutar tarea manualmente
schtasks /run /tn "Creacion Modelos LADM-COL"

REM Eliminar tarea (si es necesario)
schtasks /delete /tn "Creacion Modelos LADM-COL" /f
```

## ============================================
## EJEMPLO 7: REVISAR LOGS
## ============================================

### Ver todos los logs

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
dir log\
```

### Ver log mas reciente

```cmd
REM En PowerShell
Get-ChildItem log\creacion_modelos_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

### Buscar errores en logs

```cmd
findstr /i "error" log\*.log
```

### Ver resumen de ultima ejecucion

```cmd
findstr /i "RESUMEN exitoso error" log\creacion_modelos_*.log
```

## ============================================
## EJEMPLO 8: BACKUP DE BASE DE DATOS
## ============================================

### Backup completo

```cmd
REM Crear directorio de backups
mkdir C:\backup\postgresql

REM Backup en formato comprimido
pg_dump -h localhost -U postgres -Fc interno_v3_acc > C:\backup\postgresql\interno_v3_acc_%date:~6,4%%date:~3,2%%date:~0,2%.dump

REM Verificar backup
dir C:\backup\postgresql\
```

### Backup de un solo esquema

```cmd
pg_dump -h localhost -U postgres -Fc -n cun25019 interno_v3_acc > C:\backup\postgresql\cun25019_%date:~6,4%%date:~3,2%%date:~0,2%.dump
```

### Restaurar backup

```cmd
REM Restaurar base completa a nueva BD
createdb -h localhost -U postgres interno_v3_acc_restore
pg_restore -h localhost -U postgres -d interno_v3_acc_restore C:\backup\postgresql\interno_v3_acc_20251124.dump

REM Restaurar solo un esquema
pg_restore -h localhost -U postgres -d interno_v3_acc -n cun25019 C:\backup\postgresql\cun25019_20251124.dump
```

## ============================================
## EJEMPLO 9: RECREAR UN ESQUEMA ESPECIFICO
## ============================================

### Opcion A: Modificar config.json temporalmente

1. Editar config.json
2. Dejar solo el esquema que quieres recrear:

```json
{
    "schemas": ["cun25019"]
}
```

3. Ejecutar:
```cmd
python creacion_modelos_fisicos.py
```

4. Restaurar config.json con todos los esquemas

### Opcion B: Eliminar y recrear manualmente

```cmd
REM 1. Eliminar esquema existente
psql -h localhost -U postgres -d interno_v3_acc -c "DROP SCHEMA IF EXISTS cun25019 CASCADE; DROP SCHEMA IF EXISTS cun25019_mi CASCADE;"

REM 2. Ejecutar script (con todos los esquemas en config.json)
python creacion_modelos_fisicos.py
```

## ============================================
## EJEMPLO 10: CONSULTAR METRICAS
## ============================================

### Ver tiempo de ejecucion por esquema

```cmd
findstr "Tiempo de ejecucion" log\creacion_modelos_*.log
```

### Ver tamano de base de datos

```cmd
psql -h localhost -U postgres -d postgres -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) as size FROM pg_database WHERE datname = 'interno_v3_acc';"
```

### Ver tamano por esquema

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "SELECT schemaname, pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size FROM pg_tables WHERE schemaname LIKE 'cun25%%' AND schemaname NOT LIKE '%%_mi' GROUP BY schemaname ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;"
```

## ============================================
## EJEMPLO 11: SOLUCION DE PROBLEMAS COMUNES
## ============================================

### Problema: Script falla con "config.json not found"

```cmd
REM Verificar que el archivo existe
dir config.json

REM Si no existe, crearlo con valores por defecto
python -c "from creacion_modelos_fisicos import create_default_config; create_default_config()"

REM Editar con valores correctos
notepad config.json
```

### Problema: "java: no se reconoce como comando"

```cmd
REM Verificar Java
where java

REM Si no funciona, agregar al PATH temporalmente:
set PATH=%PATH%;C:\Program Files\Java\jre1.8.0_XXX\bin

REM O agregar permanentemente via Variables de entorno
```

### Problema: "No module named 'psycopg2'"

```cmd
pip install psycopg2-binary
```

### Problema: ili2pg timeout

Editar creacion_modelos_fisicos.py:
1. Buscar: `timeout=600`
2. Cambiar a: `timeout=1800` (30 minutos)

### Problema: Espacio en disco insuficiente

```cmd
REM Verificar espacio
wmic logicaldisk get size,freespace,caption

REM Limpiar logs antiguos (mas de 7 dias)
forfiles /p "log" /s /m *.log /d -7 /c "cmd /c del @path"

REM Limpiar backups antiguos
forfiles /p "C:\backup\postgresql" /s /m *.dump /d -30 /c "cmd /c del @path"
```

### Problema: Conexion rechazada a PostgreSQL

```cmd
REM Verificar servicio
sc query postgresql-x64-12

REM Iniciar servicio si esta detenido
net start postgresql-x64-12

REM Verificar puerto
netstat -an | findstr 5432
```

## ============================================
## EJEMPLO 12: VERIFICACION RAPIDA DEL SISTEMA
## ============================================

### Script de verificacion (guardar como verificar.bat)

```batch
@echo off
echo === VERIFICACION DEL SISTEMA ===
echo.

echo Verificando Java...
java -version 2>nul && echo [OK] Java encontrado || echo [ERROR] Java no encontrado

echo.
echo Verificando Python...
python --version 2>nul && echo [OK] Python encontrado || echo [ERROR] Python no encontrado

echo.
echo Verificando psycopg2...
python -c "import psycopg2" 2>nul && echo [OK] psycopg2 instalado || echo [ERROR] psycopg2 no instalado

echo.
echo Verificando PostgreSQL...
psql -h localhost -U postgres -d postgres -c "SELECT 1" >nul 2>&1 && echo [OK] PostgreSQL accesible || echo [ERROR] PostgreSQL no accesible

echo.
echo Verificando archivos...
if exist creacion_modelos_fisicos.py (echo [OK] Script Python) else (echo [ERROR] Script Python no encontrado)
if exist config.json (echo [OK] config.json) else (echo [ERROR] config.json no encontrado)
if exist ili2pg\ili2pg-4.4.3.jar (echo [OK] JAR ili2pg) else (echo [ERROR] JAR ili2pg no encontrado)

echo.
echo === VERIFICACION COMPLETA ===
pause
```

## ============================================
## RESUMEN DE COMANDOS MAS USADOS
## ============================================

```cmd
REM Ejecutar script manualmente
python creacion_modelos_fisicos.py

REM Ejecutar con script batch
ejecutar_creacion.bat

REM Ver logs (PowerShell)
Get-Content log\creacion_modelos_*.log -Wait -Tail 50

REM Listar esquemas creados
psql -h localhost -U postgres -d interno_v3_acc -c "\dn"

REM Ver tablas de un esquema
psql -h localhost -U postgres -d interno_v3_acc -c "\dt cun25019.*"

REM Hacer backup
pg_dump -h localhost -U postgres -Fc interno_v3_acc > backup_%date:~6,4%%date:~3,2%%date:~0,2%.dump

REM Ver tarea programada
schtasks /query /tn "Creacion Modelos LADM-COL"

REM Verificar espacio en disco
wmic logicaldisk get size,freespace,caption
```

---

**Consulta estos ejemplos siempre que necesites recordar como hacer algo!**

---

**Version:** 2.0
**Fecha:** 2025-11-24
**Plataforma:** Windows
