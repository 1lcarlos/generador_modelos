# CHECKLIST DE VALIDACION
# Creacion de Modelos Fisicos LADM-COL - Windows

## ============================================
## PRE-REQUISITOS
## ============================================

### Sistema Operativo
- [ ] Windows 10/11 (64-bit)
- [ ] Acceso de administrador disponible
- [ ] Espacio en disco: minimo 20GB libre
- [ ] Memoria RAM: minimo 4GB

## ============================================
## INSTALACION POSTGRESQL
## ============================================

### PostgreSQL 12+ con PostGIS
- [ ] PostgreSQL 12+ descargado
- [ ] PostgreSQL instalado
- [ ] PostGIS instalado via Stack Builder
- [ ] Password de postgres configurado
- [ ] PostgreSQL agregado al PATH

### Verificacion PostgreSQL

```cmd
REM Ejecutar y marcar OK si funciona:
psql --version
REM [ ] OK - Muestra version

psql -h localhost -U postgres -d postgres -c "SELECT version();"
REM [ ] OK - Conecta y muestra version

psql -h localhost -U postgres -d postgres -c "SELECT PostGIS_version();"
REM [ ] OK - Muestra version de PostGIS
```

### Servicio PostgreSQL
- [ ] Servicio ejecutandose (services.msc)
- [ ] Puerto 5432 en uso (o el configurado)

## ============================================
## INSTALACION JAVA 8
## ============================================

### Java Runtime Environment 1.8.0
- [ ] Java 8 descargado (Oracle o OpenJDK)
- [ ] Java 8 instalado
- [ ] Java en PATH
- [ ] JAVA_HOME configurado (opcional pero recomendado)

### Verificacion Java

```cmd
REM Ejecutar y verificar:
java -version
REM [ ] OK - Muestra: java version "1.8.0_XXX" o openjdk version "1.8.0_XXX"

where java
REM [ ] OK - Muestra ruta de java.exe
```

## ============================================
## INSTALACION PYTHON Y DEPENDENCIAS
## ============================================

### Python 3
- [ ] Python 3.8+ descargado
- [ ] Python instalado
- [ ] Python en PATH
- [ ] pip instalado
- [ ] psycopg2-binary instalado

### Verificacion Python

```cmd
REM Ejecutar y verificar:
python --version
REM [ ] OK - Version 3.8 o superior

pip --version
REM [ ] OK - pip instalado

python -c "import psycopg2; print('psycopg2 OK')"
REM [ ] OK - Muestra: psycopg2 OK
```

## ============================================
## ESTRUCTURA DE ARCHIVOS
## ============================================

### Directorio Principal
- [ ] Directorio windows_version existe
- [ ] Ruta accesible sin problemas de permisos

### Archivos del Proyecto

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
dir
```

- [ ] creacion_modelos_fisicos.py presente
- [ ] config.json presente
- [ ] ejecutar_creacion.bat presente
- [ ] ili2pg\ directorio presente
- [ ] ili2pg\ili2pg-4.4.3.jar presente
- [ ] ctm12\ directorio presente
- [ ] ctm12\insert_ctm12_pg.sql presente
- [ ] modelo_acc_interno\ directorio presente
- [ ] log\ directorio presente (o se creara automaticamente)

### Modelos INTERLIS

```cmd
dir modelo_acc_interno\*.ili
```

- [ ] INTERLIS_TOPOLOGY.ili presente
- [ ] ISO19107_PLANAS_V3_1.ili presente
- [ ] LADM_COL_v_4_0_1_Nucleo.ili presente
- [ ] Modelo_Interno_ACC_V3.ili presente
- [ ] Submodelo_Cartografia_Catastral_V1_1.ili presente
- [ ] Submodelo_Valoracion_Masiva_V1_0.ili presente

## ============================================
## CONFIGURACION
## ============================================

### Archivo config.json
- [ ] Archivo config.json existe
- [ ] Password actualizado (no es "TU_PASSWORD_AQUI")
- [ ] Puerto correcto (5432 por defecto en Windows)
- [ ] Nombre de base de datos correcto
- [ ] Lista de esquemas configurada
- [ ] Rutas (paths) verificadas con doble backslash

### Verificacion de Configuracion

```cmd
REM Ver contenido
type config.json

REM Verificar que el password no es el default:
findstr "TU_PASSWORD" config.json
REM [ ] OK - No debe retornar nada (password cambiado)
```

## ============================================
## VALIDACION PRE-EJECUCION
## ============================================

### Verificar Java con JAR

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
java -jar ili2pg\ili2pg-4.4.3.jar --version
REM [ ] OK - Muestra version de ili2pg
```

### Verificar Conexion PostgreSQL

```cmd
psql -h localhost -U postgres -d postgres -c "SELECT 1"
REM [ ] OK - Retorna: 1
```

### Test de Script Python

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
python -c "import json; config=json.load(open('config.json')); print('Config OK')"
REM [ ] OK - Muestra: Config OK
```

## ============================================
## PRIMERA EJECUCION
## ============================================

### Ejecucion Manual

```cmd
cd C:\ladm_col\desarrollos\creacion_modelos_fisicos\windows_version
python creacion_modelos_fisicos.py
```

- [ ] Script inicia sin errores
- [ ] Se crea base de datos interno_v3_acc
- [ ] Se habilitan extensiones PostGIS y uuid-ossp
- [ ] Se procesan todos los esquemas
- [ ] No hay errores fatales

### Monitoreo Durante Ejecucion (PowerShell)

```powershell
Get-Content log\creacion_modelos_*.log -Wait -Tail 50
REM [ ] OK - Ver progreso en tiempo real
```

## ============================================
## VALIDACION POST-EJECUCION
## ============================================

### Base de Datos Creada

```cmd
psql -h localhost -U postgres -l | findstr interno_v3_acc
REM [ ] OK - Base de datos existe
```

### Extensiones Habilitadas

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "\dx"
REM [ ] OK - PostGIS presente
REM [ ] OK - uuid-ossp presente
```

### Esquemas Creados

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "\dn" | findstr cun25
REM [ ] OK - Ver todos los esquemas
```

### Tablas por Esquema

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "SELECT schemaname, COUNT(*) as total_tablas FROM pg_tables WHERE schemaname LIKE 'cun25%%' GROUP BY schemaname ORDER BY schemaname;"
REM [ ] OK - Cada esquema tiene ~100-150 tablas
```

### Indices Espaciales

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "SELECT schemaname, COUNT(*) as indices_espaciales FROM pg_indexes WHERE indexdef ILIKE '%%USING gist%%' AND schemaname LIKE 'cun25%%' GROUP BY schemaname;"
REM [ ] OK - Cada esquema tiene multiples indices espaciales
```

### Metadatos ili2db

```cmd
psql -h localhost -U postgres -d interno_v3_acc -c "\dn" | findstr "_mi"
REM [ ] OK - Ver esquemas de metadatos: cun25019_mi, etc.
```

## ============================================
## VALIDACION DE LOGS
## ============================================

### Logs Principales

```cmd
dir log\
REM [ ] OK - Ver archivos de log creados
```

### Verificar Errores en Logs

```cmd
findstr /i "error" log\creacion_modelos_*.log
REM [ ] OK - No debe haber errores fatales

findstr /i "exitoso\|OK" log\creacion_modelos_*.log
REM [ ] OK - Debe mostrar esquemas creados exitosamente
```

## ============================================
## AUTOMATIZACION
## ============================================

### Script Batch
- [ ] ejecutar_creacion.bat creado
- [ ] Script probado manualmente

### Verificar Script Batch

```cmd
ejecutar_creacion.bat
REM [ ] OK - Ejecuta sin errores

dir log\ejecucion_*.log
REM [ ] OK - Log de ejecucion creado
```

### Tarea Programada
- [ ] Tarea creada en Programador de tareas
- [ ] Configurada con horario correcto
- [ ] Usuario con permisos adecuados

### Verificar Tarea

```cmd
schtasks /query /tn "Creacion Modelos LADM-COL"
REM [ ] OK - Muestra tarea configurada
```

## ============================================
## BACKUP Y RECUPERACION
## ============================================

### Backup Manual

```cmd
REM Crear backup de prueba
pg_dump -h localhost -U postgres -Fc interno_v3_acc > C:\backup\test_backup.dump
REM [ ] OK - Backup creado sin errores

dir C:\backup\test_backup.dump
REM [ ] OK - Archivo tiene tamano razonable
```

## ============================================
## SEGURIDAD
## ============================================

### Credenciales
- [ ] Password de PostgreSQL es fuerte
- [ ] config.json no esta en repositorio publico
- [ ] Permisos de carpeta restringidos

### Logs
- [ ] Logs no contienen passwords en texto plano

## ============================================
## CHECKLIST FINAL
## ============================================

### Resumen
- [ ] PostgreSQL 12+ con PostGIS instalado y funcionando
- [ ] Java 8 instalado y verificado
- [ ] Python 3 y dependencias instaladas
- [ ] Estructura de archivos completa
- [ ] Configuracion correcta en config.json
- [ ] Primera ejecucion exitosa
- [ ] Todos los esquemas creados correctamente
- [ ] Validacion de estructura completa
- [ ] Logs sin errores criticos
- [ ] Automatizacion configurada (tarea programada)
- [ ] Backup funcional

### Estado Final

```
[ ] SISTEMA LISTO PARA PRODUCCION
[ ] REQUIERE AJUSTES MENORES
[ ] REQUIERE REVISION COMPLETA
```

## ============================================
## NOTAS ADICIONALES
## ============================================

Fecha de validacion: ___________________
Validado por: __________________________
Observaciones:




---

**Version del Checklist:** 2.0
**Ultima actualizacion:** 2025-11-24
**Plataforma:** Windows
