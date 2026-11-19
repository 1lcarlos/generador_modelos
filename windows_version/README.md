# Administrador de Modelos LADM-COL 3.0

Aplicación para gestionar datos LADM-COL en PostgreSQL/PostGIS con **ili2pg 5.5.1** e
**ilivalidator 1.15.0**.

Flujo de trabajo: **Validar XTF → Crear esquema → Importar XTF → Exportar XTF**

## Requisitos

| Componente | Versión |
|------------|---------|
| Windows | 10/11 64-bit |
| Python | 3.10 o superior (marcar *Add Python to PATH* al instalar) |
| Java | 8 o superior (JRE) |
| PostgreSQL | 12 o superior, con la extensión PostGIS disponible en el servidor |

## Instalación y primer uso

```cmd
ejecutar_administrador.bat
```

La primera vez el lanzador hace dos cosas:

1. Instala las dependencias de `requirements.txt`: PySide6, psycopg2-binary y keyring.
2. Descarga **ili2pg** e **ilivalidator** desde `downloads.interlis.ch` a la carpeta `ili2pg/`,
   verificando su huella SHA-256. También se puede hacer a mano con `python -m ladm_admin herramientas`
   o con el botón de la página *Inicio*.

Luego, en la aplicación:

1. **Configuración → Conexiones**: cree la conexión a la base de datos. La contraseña se guarda en el
   Administrador de credenciales de Windows.
2. **Configuración → Perfiles de modelo**: revise el perfil. En el primer arranque se crea uno por cada
   carpeta de `Modelos/`.
3. Siga los pasos 1 a 4 de la barra lateral. La página **Inicio** muestra si todo está listo.

¿Usaba la versión 2.0? En **Configuración → Herramientas y general** pulse *Importar perfiles de la
versión 2.0* para traer sus conexiones y modelos.

## Línea de comandos

Usa las mismas conexiones y perfiles guardados en la interfaz:

```cmd
ejecutar_administrador.bat listar
ejecutar_administrador.bat herramientas
ejecutar_administrador.bat validar ..\entregas\ --perfil SINIC
ejecutar_administrador.bat crear --conexion local --perfil SINIC --esquemas cun25279,cun25436
ejecutar_administrador.bat importar ..\entregas\ --conexion local --perfil SINIC --si-hay-datos reemplazar --solo-analizar
ejecutar_administrador.bat exportar --conexion local --perfil SINIC --todos --salida ..\salida\
```

La contraseña se toma del Administrador de credenciales, de la variable `LADM_PGPASSWORD` o se pide por
consola. El código de salida es `1` si algún elemento falló. Detalle completo en [MANUAL.md](MANUAL.md#9-línea-de-comandos).

## Estructura

```
windows_version/
  ejecutar_administrador.bat   Lanzador (interfaz sin argumentos, CLI con argumentos)
  requirements.txt             Dependencias de ejecución
  requirements-dev.txt         Dependencias de desarrollo (pruebas)
  ladm_admin/
    core/                      Lógica sin interfaz
      operations.py            Validar, crear, importar y exportar
      ili2db.py                Comandos de ili2pg/ilivalidator y opciones de esquema
      database.py              PostgreSQL e inspección de esquemas ili2db
      xtf.py / ili.py          Lectura de XTF (cabecera, conteos, ZIP) y de modelos .ili
      settings.py              Conexiones, perfiles y credenciales
      tools_setup.py           Descarga verificada de ili2pg/ilivalidator
    ui/                        Interfaz PySide6 (pages/ = una página por paso)
    cli.py                     Línea de comandos
  tests/                       Pruebas unitarias
  Modelos/SINIC/               Modelos INTERLIS incluidos (un perfil por carpeta)
  ctm12/                       Script previo con el sistema de referencia CTM12
```

No se versionan (`.gitignore`):
- `ili2pg/`, que se descarga.
- `log/`.
- `xtf/` y cualquier `*.xtf`: datos catastrales con información personal.
- `modelo_acc_interno/`: modelo interno de la ACC. Para usarlo, cree un perfil de modelo que apunte a
  su carpeta.

## Desarrollo

```cmd
python -m pip install -r requirements-dev.txt
python -m pytest tests
python -m ladm_admin            :: abre la interfaz
```

- La lógica va en `ladm_admin/core/` y no importa nada de Qt; la interfaz y el CLI solo la usan.
- Las operaciones informan su avance con un `Reporter` y se detienen con un `CancelToken`. La interfaz
  las ejecuta en segundo plano (`ui/worker.py`).
- La configuración del usuario se guarda en `%APPDATA%\LADMAdmin\settings.json`.
- Para actualizar ili2pg o ilivalidator, cambie la versión en `core/paths.py` y la URL y la huella
  SHA-256 en `core/tools_setup.py`.

## Distribución

Para entregar la herramienta sin git, comprima la carpeta `windows_version/` excluyendo `log/`, `xtf/`
y `__pycache__/`. Puede incluir `ili2pg/` si los equipos de destino no tienen internet. El destinatario
solo necesita Python, Java y ejecutar `ejecutar_administrador.bat`.

---

**Versión 3.0.0** | **Agencia Catastral de Cundinamarca**
