# Administrador de Modelos LADM

Herramienta para gestionar esquemas LADM-COL en PostgreSQL/PostGIS.

## Funcionalidades

- **Crear Esquemas**: Genera modelos fisicos a partir de archivos INTERLIS (.ili) usando ili2pg
- **Exportar XTF**: Exporta datos de esquemas a archivos XTF
- **Validar XTF**: Valida archivos XTF contra modelos INTERLIS usando ilivalidator

## Inicio rapido

```cmd
ejecutar_interfaz.bat
```

## Requisitos

- Windows 10/11 (64-bit)
- Python 3.8+ (con `pip install psycopg2-binary`)
- Java 8 (JRE 1.8.0)
- PostgreSQL 12+ con PostGIS

## Uso por linea de comandos

```cmd
REM Copiar y editar configuracion
copy config.json.ejemplo config.json
notepad config.json

REM Ejecutar
ejecutar_creacion.bat
```

## Documentacion completa

Consulte **[MANUAL.md](MANUAL.md)** para instrucciones detalladas de instalacion, configuracion y uso de todos los modulos.

---

**Version 2.0** | **Agencia Catastral de Cundinamarca**
