"""Administrador de Modelos LADM-COL.

Herramienta de la Agencia Catastral de Cundinamarca (ACC) para validar archivos
XTF, crear esquemas LADM-COL en PostgreSQL/PostGIS, importar y exportar datos
usando ili2pg e ilivalidator.

El paquete se divide en:
    core/   lógica independiente de la interfaz (usada por la GUI y el CLI)
    ui/     interfaz gráfica (PySide6)
    cli.py  línea de comandos
"""

APP_NAME = "Administrador de Modelos LADM-COL"
APP_ORG = "Agencia Catastral de Cundinamarca"
APP_SHORT = "LADMAdmin"
__version__ = "3.0.0"
