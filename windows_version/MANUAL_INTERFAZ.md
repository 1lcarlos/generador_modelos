# MANUAL DE LA INTERFAZ GRAFICA
# Generador de Modelos INTERLIS
# Agencia Catastral de Cundinamarca (ACC)

## INTRODUCCION

La interfaz grafica permite generar modelos fisicos en PostgreSQL/PostGIS a partir de cualquier archivo INTERLIS (.ili) de forma facil e intuitiva, sin necesidad de editar archivos de configuracion.

## REQUISITOS

- Windows 10/11
- Python 3.8+
- PostgreSQL 12+ con PostGIS
- Java 8 (JRE 1.8.0)
- Libreria psycopg2-binary

## INICIO RAPIDO

### Opcion 1: Usar el script batch

```cmd
ejecutar_interfaz.bat
```

### Opcion 2: Ejecutar directamente

```cmd
python interfaz_ili2pg.py
```

---

## DESCRIPCION DE LA INTERFAZ

La interfaz tiene 3 pestanas principales:

### Pestana 1: Configuracion

Esta pestana contiene toda la configuracion necesaria.

#### Seccion: Perfiles de Configuracion

Permite guardar y cargar configuraciones para reutilizar:

- **Perfil**: Seleccionar un perfil guardado
- **Cargar**: Cargar el perfil seleccionado
- **Guardar**: Guardar cambios en el perfil actual
- **Guardar Como...**: Crear nuevo perfil con la configuracion actual
- **Eliminar**: Eliminar el perfil seleccionado

**Uso recomendado**: Crear perfiles para diferentes entornos (Desarrollo, Pruebas, Produccion).

#### Seccion: Rutas de Archivos

- **Archivo ili2pg.jar**: Ruta al archivo JAR de ili2pg (ej: `ili2pg-4.4.3.jar`)
- **Script CTM12 (SQL)**: Ruta al script SQL de CTM12 (opcional pero recomendado)
- **Carpeta de modelos**: Carpeta que contiene los archivos .ili
- **Carpeta de logs**: Donde se guardaran los logs de ejecucion

Usar el boton "Examinar..." para seleccionar cada archivo/carpeta.

#### Seccion: Modelos INTERLIS Disponibles

Muestra los archivos .ili encontrados en la carpeta de modelos.

- **Actualizar Lista**: Recargar lista de archivos .ili
- **Lista de modelos**: Click en un modelo para seleccionarlo
- **Modelo seleccionado**: Muestra el modelo actualmente seleccionado

#### Seccion: Conexion a Base de Datos

- **Host**: Servidor PostgreSQL (default: localhost)
- **Puerto**: Puerto de PostgreSQL (default: 5432)
- **Base de datos**: Nombre de la BD destino (se crea si no existe)
- **Usuario**: Usuario de PostgreSQL (default: postgres)
- **Password**: Contrasena del usuario
- **Mostrar**: Checkbox para ver/ocultar password
- **Probar Conexion**: Verificar que la conexion funciona

#### Seccion: Esquemas a Crear

Ingresar los nombres de los esquemas, uno por linea:

```
cun25019
cun25035
cun25436
```

Tambien se pueden separar por comas en una linea:

```
cun25019, cun25035, cun25436
```

#### Seccion: Sistema de Referencia Espacial

- **Codigo EPSG**: Codigo del sistema de coordenadas (default: 9377 para MAGNA-SIRGAS/CTM12)

---

### Pestana 2: Opciones ili2pg

Permite configurar las opciones avanzadas de ili2pg:

#### Botones Rapidos

- **Seleccionar Todas**: Activar todas las opciones
- **Deseleccionar Todas**: Desactivar todas las opciones
- **Restaurar Predeterminadas**: Volver a valores por defecto

#### Opciones Disponibles

| Opcion | Descripcion |
|--------|-------------|
| setupPgExt | Configurar extensiones PostgreSQL |
| coalesceCatalogueRef | Unir referencias de catalogo |
| createEnumTabs | Crear tablas de enumeracion |
| createNumChecks | Crear validaciones numericas |
| coalesceMultiSurface | Unir multi-superficies |
| coalesceMultiLine | Unir multi-lineas |
| coalesceMultiPoint | Unir multi-puntos |
| coalesceArray | Unir arrays |
| beautifyEnumDispName | Embellecer nombres de enumeracion |
| createUnique | Crear constraints unicos |
| createGeomIdx | Crear indices geometricos |
| createFk | Crear llaves foraneas |
| createFkIdx | Crear indices de FK |
| createMetaInfo | Crear informacion de metadatos |
| expandMultilingual | Expandir campos multilingues |
| createTypeConstraint | Crear constraints de tipo |
| createEnumTabsWithId | Tablas enum con ID |
| createTidCol | Crear columna TID |
| smart2Inheritance | Herencia inteligente tipo 2 |
| strokeArcs | Convertir arcos a segmentos |

**Recomendacion**: Mantener las opciones predeterminadas para el modelo LADM-COL.

---

### Pestana 3: Ejecucion

#### Vista Previa del Comando

Muestra el comando ili2pg que se ejecutara (con password oculto).

- **Actualizar Vista Previa**: Regenerar la vista previa
- **Copiar Comando**: Copiar al portapapeles

#### Controles de Ejecucion

- **Recrear esquemas existentes**: Si esta marcado, elimina esquemas existentes antes de crearlos
- **EJECUTAR**: Iniciar el proceso de creacion
- **DETENER**: Detener el proceso en curso

#### Log de Ejecucion

Muestra el progreso en tiempo real con colores:

- **Negro**: Informacion general
- **Verde**: Exito
- **Rojo**: Error
- **Naranja**: Advertencia
- **Azul**: Comando

Botones del log:
- **Limpiar Log**: Borrar contenido
- **Guardar Log**: Exportar a archivo

---

## FLUJO DE TRABAJO TIPICO

### 1. Configurar rutas

1. Seleccionar archivo ili2pg.jar
2. Seleccionar script CTM12 (opcional)
3. Seleccionar carpeta con modelos .ili
4. Seleccionar carpeta para logs

### 2. Seleccionar modelo

1. La lista se actualiza automaticamente
2. Click en el modelo deseado
3. Verificar que aparece en "Modelo seleccionado"

### 3. Configurar base de datos

1. Ingresar host, puerto, usuario, password
2. Ingresar nombre de la base de datos destino
3. Probar conexion

### 4. Definir esquemas

1. Ingresar nombres de esquemas (uno por linea)
2. Ejemplo: cun25019, cun25035, etc.

### 5. Guardar perfil (opcional)

1. Click en "Guardar Como..."
2. Ingresar nombre descriptivo
3. El perfil queda disponible para uso futuro

### 6. Ejecutar

1. Ir a pestana "Ejecucion"
2. Revisar vista previa del comando
3. Click en "EJECUTAR"
4. Monitorear progreso en el log
5. Revisar resumen al finalizar

---

## PERFILES DE CONFIGURACION

### Crear un perfil

1. Configurar todos los parametros
2. Click en "Guardar Como..."
3. Ingresar nombre (ej: "Produccion", "Desarrollo")
4. Click Aceptar

### Cargar un perfil

1. Seleccionar perfil del dropdown
2. Click en "Cargar"
3. Todos los campos se actualizan

### Modificar un perfil

1. Cargar el perfil
2. Hacer cambios
3. Click en "Guardar"

### Eliminar un perfil

1. Seleccionar perfil
2. Click en "Eliminar"
3. Confirmar

### Ubicacion de perfiles

Los perfiles se guardan en:
```
%USERPROFILE%\.ili2pg_gui\profiles.json
```

---

## SOLUCION DE PROBLEMAS

### Error: "Python no esta instalado"

Instalar Python desde: https://www.python.org/downloads/
Asegurar que "Add Python to PATH" este marcado.

### Error: "Libreria psycopg2 no instalada"

```cmd
pip install psycopg2-binary
```

### Error: "Java no encontrado"

Verificar que Java 8 esta instalado y en el PATH:
```cmd
java -version
```

### Error: "No se pudo conectar a la base de datos"

1. Verificar que PostgreSQL esta corriendo
2. Verificar host, puerto, usuario, password
3. Verificar que el firewall permite conexiones

### El proceso se queda colgado

1. Click en "DETENER"
2. Verificar logs de ili2pg en la carpeta de logs
3. Aumentar timeout si es necesario (editar script)

### Los esquemas no se crean

1. Revisar log de ejecucion
2. Verificar que el modelo .ili es correcto
3. Verificar que todas las dependencias del modelo estan en la carpeta

---

## TIPS Y RECOMENDACIONES

### Organizacion de modelos

Colocar todos los archivos .ili relacionados en la misma carpeta:
```
modelo_acc_interno/
    INTERLIS_TOPOLOGY.ili
    ISO19107_PLANAS_V3_1.ili
    LADM_COL_v_4_0_1_Nucleo.ili
    Modelo_Interno_ACC_V3.ili
    Submodelo_Cartografia_Catastral_V1_1.ili
    Submodelo_Valoracion_Masiva_V1_0.ili
```

### Multiples bases de datos

Crear un perfil para cada base de datos destino.

### Ejecucion masiva

Para muchos esquemas, considerar ejecutar por lotes para poder monitorear mejor.

### Logs

Siempre especificar carpeta de logs para tener historial de ejecuciones.

### Backups

Hacer backup de la BD antes de recrear esquemas existentes.

---

## ATAJOS DE TECLADO

- **Ctrl+Q**: Cerrar aplicacion
- **F5**: Actualizar lista de modelos
- **Ctrl+Enter**: Ejecutar (en pestana Ejecucion)

---

## ARCHIVOS DE LA APLICACION

```
windows_version/
    interfaz_ili2pg.py      <- Codigo fuente de la interfaz
    ejecutar_interfaz.bat   <- Script para iniciar la interfaz
    MANUAL_INTERFAZ.md      <- Este manual

%USERPROFILE%\.ili2pg_gui/
    profiles.json           <- Perfiles guardados
    last_profile.json       <- Ultima configuracion usada
```

---

## SOPORTE

Para problemas o sugerencias:
- Revisar este manual
- Consultar documentacion de ili2pg: https://github.com/claeis/ili2db
- Contactar al Area de Desarrollo ACC

---

**Version:** 1.0
**Fecha:** 2025
**Autor:** ACC - Area de Desarrollo
