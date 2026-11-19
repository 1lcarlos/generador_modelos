@echo off
REM Administrador de Modelos LADM-COL 3.0
REM Agencia Catastral de Cundinamarca (ACC)
REM
REM Sin argumentos abre la interfaz grafica.
REM Con argumentos ejecuta la linea de comandos, por ejemplo:
REM   ejecutar_administrador.bat validar xtf\ --perfil SINIC
REM   ejecutar_administrador.bat importar xtf\25279 --conexion local --perfil SINIC --si-hay-datos reemplazar

setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Instale Python 3.10 o superior desde https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import PySide6, psycopg2, keyring" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias por primera vez...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

REM ili2pg e ilivalidator no se versionan: se descargan la primera vez
if not exist "ili2pg\ili2pg-5.5.1\ili2pg-5.5.1.jar" goto descargar
if not exist "ili2pg\ilivalidator-1.15.0\ilivalidator-1.15.0.jar" goto descargar
goto ejecutar
:descargar
echo Descargando ili2pg e ilivalidator (solo la primera vez)...
python -m ladm_admin herramientas
if errorlevel 1 (
    echo [AVISO] No se pudieron descargar las herramientas. Puede reintentarlo desde la pagina Inicio.
)

:ejecutar
if "%~1"=="" (
    start "" pythonw -m ladm_admin
) else (
    python -m ladm_admin %*
)
