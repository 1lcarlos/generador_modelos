@echo off
REM Script para ejecutar el Administrador de Modelos LADM
REM Agencia Catastral de Cundinamarca (ACC)

echo.
echo ==========================================
echo   Administrador de Modelos LADM
echo   Agencia Catastral de Cundinamarca
echo ==========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH
    echo Por favor, instale Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verificar psycopg2
python -c "import psycopg2" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Instalando psycopg2-binary...
    pip install psycopg2-binary
)

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Ejecutar interfaz
echo Iniciando interfaz grafica...
python interfaz_ili2pg.py

if errorlevel 1 (
    echo.
    echo [ERROR] La interfaz termino con errores
    pause
)
