# Historial de versiones

## 3.0.0 - 2026-11-19

Reescritura completa. La versión 2.0 (Tkinter) se retiró del repositorio; está disponible en la
etiqueta `v2.0`.

### Nuevo
- **Importar XTF**, con análisis previo del plan:
  - Estados por archivo: listo, con datos o bloqueado.
  - Políticas ante datos existentes: reemplazar, agregar como nuevo dataset, omitir o preguntar.
  - Verificación de conteos por clase después de importar.
- Soporte para **dos modos de almacenamiento**: un esquema por municipio o un esquema único con datasets.
- Interfaz **PySide6** con flujo guiado de 4 pasos, página de Inicio con el estado del entorno, tema
  claro/oscuro y tabla filtrable de errores de validación.
- **Conexiones y perfiles de modelo** reutilizables. Las contraseñas van al Administrador de
  credenciales de Windows.
- **Línea de comandos** (`python -m ladm_admin`) sobre el mismo núcleo que la interfaz.
- Lectura de archivos `.zip` con XTF y búsqueda recursiva en carpetas.
- Descarga de ili2pg/ilivalidator con versiones fijas y verificación SHA-256 (`python -m ladm_admin herramientas`).
- Migración de perfiles de la versión 2.0.
- Pruebas unitarias e integración continua.

### Cambios
- Un solo lanzador, `ejecutar_administrador.bat` (interfaz o CLI), en lugar de `ejecutar_interfaz.bat` y
  `ejecutar_creacion.bat`. `config.json` ya no se usa: el CLI comparte las conexiones y perfiles de la
  interfaz.
- ili2pg e ilivalidator ya no se distribuyen en el repositorio: se descargan la primera vez.
- Versión única de **ili2pg 5.5.1** (antes convivían 4.4.3 y 5.5.1).
- Al crear un esquema se pasan todos los modelos con contenido a `--models`. Antes se podían omitir
  modelos y sus clases quedaban sin tablas.
- **Recrear un esquema es seguro:** el original se respalda y se restaura si la creación falla.
- Las herramientas se ejecutan sin `cmd.exe`; *Detener* finaliza realmente el proceso Java.
- La exportación toma los modelos del propio esquema (`t_ili2db_model`), no de la carpeta de modelos.
- El log de exportación ahora se llama `<código>_exportacion.log` (antes `<código>.txt`).

### Corregido (respecto a 2.0)
- "Copiar comando" fallaba (`selected_model` inexistente).
- "Guardar log" fallaba en las tres pestañas (`initialfilename`).
- Actualización de widgets desde hilos secundarios (posibles bloqueos).
- Contraseñas guardadas en texto plano en los perfiles.
- Líneas del log marcadas como error por contener la palabra "error".

### Limitaciones conocidas
- ili2pg solo acepta la contraseña con `--dbpwd`: se oculta en pantalla y logs, pero es visible en el
  administrador de tareas mientras se ejecuta.

## 2.0 - 2026-02-24

Interfaz Tkinter con pestañas de configuración, creación de esquemas, exportación y validación de XTF.
