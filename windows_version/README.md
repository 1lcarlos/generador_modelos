# Creacion de Modelos Fisicos LADM-COL - Windows

Sistema para la creacion automatica de modelos fisicos de bases de datos PostgreSQL/PostGIS basados en archivos INTERLIS (.ili) bajo el estandar LADM-COL.

## Dos Formas de Uso

### Opcion 1: Interfaz Grafica (Recomendada para usuarios)

```cmd
ejecutar_interfaz.bat
```

La interfaz grafica permite:
- Seleccionar archivos y carpetas visualmente
- Guardar perfiles de configuracion reutilizables
- Ver lista de modelos .ili disponibles
- Vista previa del comando antes de ejecutar
- Monitorear progreso en tiempo real
- Funciona con CUALQUIER modelo INTERLIS

**Manual completo**: [MANUAL_INTERFAZ.md](MANUAL_INTERFAZ.md)

### Opcion 2: Linea de Comandos (Para automatizacion)

```cmd
REM 1. Editar configuracion
notepad config.json

REM 2. Ejecutar
python creacion_modelos_fisicos.py
```

**Documentacion**: [README_PRINCIPAL.md](README_PRINCIPAL.md)

---

## Documentacion Completa

| Archivo | Descripcion |
|---------|-------------|
| [MANUAL_INTERFAZ.md](MANUAL_INTERFAZ.md) | Manual de la interfaz grafica |
| [README_PRINCIPAL.md](README_PRINCIPAL.md) | Guia de inicio rapido (CLI) |
| [INSTALACION_COMPLETA.md](INSTALACION_COMPLETA.md) | Guia paso a paso detallada |
| [CHECKLIST_VALIDACION.md](CHECKLIST_VALIDACION.md) | Lista de verificacion |
| [EJEMPLOS_DE_USO.md](EJEMPLOS_DE_USO.md) | Ejemplos practicos |
| [RESUMEN_EJECUTIVO.md](RESUMEN_EJECUTIVO.md) | Resumen del proyecto |

## Requisitos

- Windows 10/11 (64-bit)
- PostgreSQL 12+ con PostGIS
- Java 8 (JRE 1.8.0)
- Python 3.8+
- psycopg2-binary (`pip install psycopg2-binary`)

## Estructura

```
windows_version/
    interfaz_ili2pg.py             <- Interfaz grafica
    ejecutar_interfaz.bat          <- Iniciar interfaz
    creacion_modelos_fisicos.py    <- Script CLI
    ejecutar_creacion.bat          <- Wrapper CLI
    config.json                    <- Configuracion CLI
    ili2pg/                        <- Herramienta INTERLIS
    ctm12/                         <- Script CTM12
    modelo_acc_interno/            <- Modelos .ili
    log/                           <- Logs de ejecucion
```

---

**Version:** 2.0 | **Fecha:** 2025 | **Agencia Catastral de Cundinamarca**
