@echo off
REM Script wrapper para ejecutar creacion de modelos LADM-COL
REM Agencia Catastral de Cundinamarca (ACC)
REM Version Windows

setlocal EnableDelayedExpansion

REM Variables
set BASE_DIR=%~dp0
set LOG_DIR=%BASE_DIR%log
set TIMESTAMP=%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set EXEC_LOG=%LOG_DIR%\ejecucion_%TIMESTAMP%.log

REM Crear directorio de logs si no existe
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Inicio
echo ==========================================  >> "%EXEC_LOG%"
echo [%date% %time%] INICIO - Creacion de Modelos LADM-COL >> "%EXEC_LOG%"
echo ==========================================  >> "%EXEC_LOG%"
echo.
echo ==========================================
echo   CREACION DE MODELOS LADM-COL
echo   Agencia Catastral de Cundinamarca
echo ==========================================
echo.

REM Verificar que el directorio base existe
if not exist "%BASE_DIR%" (
    echo [ERROR] Directorio base no encontrado: %BASE_DIR%
    echo [ERROR] Directorio base no encontrado: %BASE_DIR% >> "%EXEC_LOG%"
    exit /b 1
)

REM Verificar que el script Python existe
if not exist "%BASE_DIR%creacion_modelos_fisicos.py" (
    echo [ERROR] Script Python no encontrado: creacion_modelos_fisicos.py
    echo [ERROR] Script Python no encontrado: creacion_modelos_fisicos.py >> "%EXEC_LOG%"
    exit /b 1
)
echo [OK] Script Python encontrado
echo [OK] Script Python encontrado >> "%EXEC_LOG%"

REM Verificar que config.json existe
if not exist "%BASE_DIR%config.json" (
    echo [ERROR] Archivo de configuracion no encontrado: config.json
    echo [ERROR] Archivo de configuracion no encontrado: config.json >> "%EXEC_LOG%"
    exit /b 1
)
echo [OK] Archivo de configuracion encontrado
echo [OK] Archivo de configuracion encontrado >> "%EXEC_LOG%"

REM Verificar Java
java -version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Java no esta instalado o no esta en el PATH
    echo [ERROR] Java no esta instalado o no esta en el PATH >> "%EXEC_LOG%"
    exit /b 1
)
echo [OK] Java encontrado
echo [OK] Java encontrado >> "%EXEC_LOG%"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python no esta instalado
        echo [ERROR] Python no esta instalado >> "%EXEC_LOG%"
        exit /b 1
    )
)
echo [OK] Python encontrado
echo [OK] Python encontrado >> "%EXEC_LOG%"

echo.
echo [INFO] Todos los prerequisitos verificados OK
echo [INFO] Todos los prerequisitos verificados OK >> "%EXEC_LOG%"
echo.

REM Ejecutar script Python
echo [INFO] Ejecutando creacion_modelos_fisicos.py...
echo [INFO] Ejecutando creacion_modelos_fisicos.py... >> "%EXEC_LOG%"
echo.

cd /d "%BASE_DIR%"
python creacion_modelos_fisicos.py >> "%EXEC_LOG%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ==========================================  >> "%EXEC_LOG%"
echo [%date% %time%] FIN - Codigo de salida: %EXIT_CODE% >> "%EXEC_LOG%"
echo ==========================================  >> "%EXEC_LOG%"

REM Verificar resultado
if %EXIT_CODE% EQU 0 (
    echo [OK] Proceso completado exitosamente
    echo [OK] Proceso completado exitosamente >> "%EXEC_LOG%"
) else (
    echo [ERROR] Proceso termino con errores (codigo: %EXIT_CODE%)
    echo [ERROR] Proceso termino con errores (codigo: %EXIT_CODE%) >> "%EXEC_LOG%"
)

echo.
echo [INFO] Log completo disponible en: %EXEC_LOG%
echo.

REM Pausar para ver resultados (comentar si se ejecuta desde tarea programada)
pause

exit /b %EXIT_CODE%
