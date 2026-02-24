#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para creacion de modelos fisicos LADM-COL usando ili2pg
Agencia Catastral de Cundinamarca (ACC)

Autor: ACC - Area de Desarrollo
Version: 2.0
Fecha: 2025-11-24
Plataforma: Windows
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ============================================
# CONFIGURACION
# ============================================

# Cargar configuracion desde archivo externo
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    """Cargar configuracion desde archivo JSON"""
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: Archivo de configuracion no encontrado: {CONFIG_FILE}")
        print("Creando archivo de configuracion de ejemplo...")
        create_default_config()
        sys.exit(1)

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_default_config():
    """Crear archivo de configuracion por defecto"""
    # Obtener directorio actual del script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    default_config = {
        "database": {
            "host": "localhost",
            "port": "5432",
            "database": "interno_v3_acc",
            "user": "postgres",
            "password": "TU_PASSWORD_AQUI"
        },
        "schemas": [
            "cun25019",
            "cun25035",
            "cun25436",
            "cun25040",
            "cun25053",
            "cun25095"
        ],
        "paths": {
            "base_dir": script_dir,
            "jar": "ili2pg\\ili2pg-4.4.3.jar",
            "ctm12": "ctm12\\insert_ctm12_pg.sql",
            "model": "modelo_acc_interno\\Modelo_Interno_ACC_V3.ili",
            "log_dir": "log"
        },
        "ili2pg": {
            "srs_code": "9377",
            "options": {
                "setupPgExt": True,
                "coalesceCatalogueRef": True,
                "createEnumTabs": True,
                "createNumChecks": True,
                "coalesceMultiSurface": True,
                "coalesceMultiLine": True,
                "coalesceMultiPoint": True,
                "coalesceArray": True,
                "beautifyEnumDispName": True,
                "createUnique": True,
                "createGeomIdx": True,
                "createFk": True,
                "createFkIdx": True,
                "createMetaInfo": True,
                "expandMultilingual": True,
                "createTypeConstraint": True,
                "createEnumTabsWithId": True,
                "createTidCol": True,
                "smart2Inheritance": True,
                "strokeArcs": True
            }
        }
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=4, ensure_ascii=False)

    print(f"Archivo de configuracion creado: {CONFIG_FILE}")
    print("Por favor, edita el archivo con tus credenciales y rutas correctas.")

# ============================================
# CONFIGURACION DE LOGGING
# ============================================

def setup_logging(log_dir):
    """Configurar sistema de logging"""
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'creacion_modelos_{timestamp}.log')

    # Configurar formato detallado
    log_format = '%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Configurar handlers
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return log_file

# ============================================
# GESTION DE BASE DE DATOS
# ============================================

class DatabaseManager:
    """Clase para gestionar operaciones de base de datos"""

    def __init__(self, config):
        self.config = config
        self.conn = None

    def connect(self, database='postgres'):
        """Conectar a PostgreSQL"""
        try:
            conn_params = {
                'host': self.config['database']['host'],
                'port': self.config['database']['port'],
                'database': database,
                'user': self.config['database']['user'],
                'password': self.config['database']['password']
            }

            self.conn = psycopg2.connect(**conn_params)
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logging.info(f"[OK] Conexion exitosa a base de datos: {database}")
            return True

        except Exception as e:
            logging.error(f"[ERROR] Error conectando a base de datos: {e}")
            return False

    def database_exists(self, dbname):
        """Verificar si una base de datos existe"""
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (dbname,)
            )
            exists = cur.fetchone() is not None
            cur.close()
            return exists
        except Exception as e:
            logging.error(f"Error verificando base de datos: {e}")
            return False

    def create_database(self, dbname):
        """Crear base de datos si no existe"""
        try:
            if self.database_exists(dbname):
                logging.info(f"[AVISO] Base de datos '{dbname}' ya existe")
                return True

            cur = self.conn.cursor()
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            cur.close()
            logging.info(f"[OK] Base de datos '{dbname}' creada exitosamente")
            return True

        except Exception as e:
            logging.error(f"[ERROR] Error creando base de datos: {e}")
            return False

    def enable_extensions(self, dbname):
        """Habilitar extensiones PostGIS y uuid-ossp"""
        try:
            # Conectar a la base de datos especifica
            if self.conn:
                self.conn.close()

            if not self.connect(database=dbname):
                return False

            cur = self.conn.cursor()

            # Habilitar PostGIS
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            logging.info(f"[OK] Extension PostGIS habilitada en '{dbname}'")

            # Habilitar uuid-ossp
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            logging.info(f"[OK] Extension uuid-ossp habilitada en '{dbname}'")

            cur.close()
            return True

        except Exception as e:
            logging.error(f"[ERROR] Error habilitando extensiones: {e}")
            return False

    def schema_exists(self, schema):
        """Verificar si un esquema existe"""
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,)
            )
            exists = cur.fetchone() is not None
            cur.close()
            return exists
        except Exception as e:
            logging.error(f"Error verificando esquema: {e}")
            return False

    def drop_schema(self, schema):
        """Eliminar esquema si existe (para proceso idempotente)"""
        try:
            if not self.schema_exists(schema):
                return True

            cur = self.conn.cursor()
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            cur.close()
            logging.info(f"[OK] Esquema '{schema}' eliminado para recreacion")
            return True

        except Exception as e:
            logging.error(f"[ERROR] Error eliminando esquema: {e}")
            return False

    def validate_schema_structure(self, schema):
        """Validar estructura completa del esquema creado"""
        validation_results = {
            'schema_exists': False,
            'tables_count': 0,
            'constraints_count': 0,
            'indexes_count': 0,
            'spatial_indexes_count': 0,
            'domain_tables_count': 0,
            'metadata_tables': False
        }

        try:
            cur = self.conn.cursor()

            # Verificar que el esquema existe
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,)
            )
            validation_results['schema_exists'] = cur.fetchone() is not None

            if not validation_results['schema_exists']:
                cur.close()
                return validation_results

            # Contar tablas
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (schema,)
            )
            validation_results['tables_count'] = cur.fetchone()[0]

            # Contar constraints
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema = %s",
                (schema,)
            )
            validation_results['constraints_count'] = cur.fetchone()[0]

            # Contar indices
            cur.execute(
                "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = %s",
                (schema,)
            )
            validation_results['indexes_count'] = cur.fetchone()[0]

            # Contar indices espaciales (GIST)
            cur.execute(
                "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = %s AND indexdef ILIKE '%%USING gist%%'",
                (schema,)
            )
            validation_results['spatial_indexes_count'] = cur.fetchone()[0]

            # Contar tablas de dominio (terminan en 'tipo')
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name LIKE '%%tipo'",
                (schema,)
            )
            validation_results['domain_tables_count'] = cur.fetchone()[0]

            # Verificar tablas de metadatos ili2db
            schema_mi = f"{schema}_mi"
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema_mi,)
            )
            validation_results['metadata_tables'] = cur.fetchone() is not None

            cur.close()

        except Exception as e:
            logging.error(f"Error validando estructura del esquema: {e}")

        return validation_results

    def close(self):
        """Cerrar conexion"""
        if self.conn:
            self.conn.close()
            logging.info("[OK] Conexion a base de datos cerrada")

# ============================================
# GENERACION DE MODELOS INTERLIS
# ============================================

class InterlisModelGenerator:
    """Clase para generar modelos fisicos usando ili2pg"""

    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.base_dir = config['paths']['base_dir']

        # Rutas absolutas (adaptadas para Windows)
        self.jar_path = os.path.join(self.base_dir, config['paths']['jar'])
        self.ctm12_path = os.path.join(self.base_dir, config['paths']['ctm12'])
        self.model_path = os.path.join(self.base_dir, config['paths']['model'])
        self.log_dir = os.path.join(self.base_dir, config['paths']['log_dir'])

        # Crear directorio de logs si no existe
        os.makedirs(self.log_dir, exist_ok=True)

    def validate_prerequisites(self):
        """Validar que todos los requisitos estan presentes"""
        all_ok = True

        # Verificar Java
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True  # Necesario en Windows
            )
            # En Windows, java -version escribe en stderr
            java_output = result.stderr if result.stderr else result.stdout
            java_version = java_output.split('\n')[0] if java_output else "Version desconocida"
            logging.info(f"[OK] Java encontrado: {java_version}")

            # Verificar que es Java 8
            if '1.8.0' not in java_version and '"8' not in java_version.lower():
                logging.warning(f"[AVISO] Se recomienda Java 8 para ili2pg. Version actual: {java_version}")

        except Exception as e:
            logging.error(f"[ERROR] Java no encontrado o no accesible: {e}")
            logging.error("Asegurese de que Java este instalado y en el PATH del sistema")
            all_ok = False

        # Verificar archivo JAR
        if not os.path.exists(self.jar_path):
            logging.error(f"[ERROR] Archivo JAR no encontrado: {self.jar_path}")
            all_ok = False
        else:
            logging.info(f"[OK] JAR encontrado: {self.jar_path}")

        # Verificar script CTM12
        if not os.path.exists(self.ctm12_path):
            logging.error(f"[ERROR] Script CTM12 no encontrado: {self.ctm12_path}")
            all_ok = False
        else:
            logging.info(f"[OK] Script CTM12 encontrado: {self.ctm12_path}")

        # Verificar modelo INTERLIS
        if not os.path.exists(self.model_path):
            logging.error(f"[ERROR] Modelo INTERLIS no encontrado: {self.model_path}")
            all_ok = False
        else:
            logging.info(f"[OK] Modelo INTERLIS encontrado: {self.model_path}")

        return all_ok

    def build_ili2pg_command(self, schema):
        """Construir comando ili2pg con todas las opciones"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(self.log_dir, f'ili2pg_{schema}_{timestamp}.log')

        cmd = [
            'java', '-jar', self.jar_path,
            '--schemaimport',
            '--dbhost', self.config['database']['host'],
            '--dbport', self.config['database']['port'],
            '--dbusr', self.config['database']['user'],
            '--dbpwd', self.config['database']['password'],
            '--dbdatabase', self.config['database']['database'],
            '--dbschema', schema,
            '--defaultSrsCode', self.config['ili2pg']['srs_code'],
            '--preScript', self.ctm12_path,
            '--log', log_file
        ]

        # Agregar opciones booleanas
        for option, enabled in self.config['ili2pg']['options'].items():
            if enabled:
                cmd.append(f'--{option}')

        # Agregar modelo INTERLIS al final
        cmd.append(self.model_path)

        return cmd, log_file

    def generate_schema(self, schema, recreate=False):
        """Generar modelo fisico para un esquema"""
        start_time = time.time()

        logging.info(f"\n{'='*60}")
        logging.info(f"Generando esquema: {schema}")
        logging.info(f"{'='*60}\n")

        # Si recreate=True, eliminar esquema existente
        if recreate and self.db_manager.schema_exists(schema):
            logging.info(f"Eliminando esquema existente '{schema}' para recreacion...")
            if not self.db_manager.drop_schema(schema):
                logging.error(f"[ERROR] Error eliminando esquema '{schema}'")
                return None

        # Construir comando
        cmd, log_file = self.build_ili2pg_command(schema)

        # Log del comando (sin password)
        cmd_display = cmd.copy()
        try:
            pwd_index = cmd_display.index('--dbpwd')
            cmd_display[pwd_index + 1] = '****'
        except ValueError:
            pass

        logging.info(f"Ejecutando ili2pg: {' '.join(cmd_display)}")

        # Ejecutar ili2pg
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos timeout
                shell=True  # Necesario en Windows para encontrar java
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                logging.info(f"[OK] Esquema '{schema}' creado exitosamente")
                logging.info(f"[TIEMPO] Tiempo de ejecucion: {execution_time:.2f} segundos")
                logging.info(f"[LOG] Log detallado en: {log_file}")

                # Validar estructura
                validation = self.db_manager.validate_schema_structure(schema)
                self.log_validation_results(schema, validation)

                return {
                    'schema': schema,
                    'success': True,
                    'execution_time': execution_time,
                    'log_file': log_file,
                    'validation': validation
                }
            else:
                logging.error(f"[ERROR] Error creando esquema '{schema}'")
                logging.error(f"Codigo de salida: {result.returncode}")
                if result.stderr:
                    logging.error(f"Error: {result.stderr}")
                if result.stdout:
                    logging.error(f"Salida: {result.stdout}")

                return {
                    'schema': schema,
                    'success': False,
                    'execution_time': execution_time,
                    'log_file': log_file,
                    'error': result.stderr or result.stdout
                }

        except subprocess.TimeoutExpired:
            logging.error(f"[ERROR] Timeout ejecutando ili2pg para esquema '{schema}'")
            return {
                'schema': schema,
                'success': False,
                'error': 'Timeout despues de 10 minutos'
            }
        except Exception as e:
            logging.error(f"[ERROR] Error ejecutando ili2pg: {e}")
            return {
                'schema': schema,
                'success': False,
                'error': str(e)
            }

    def log_validation_results(self, schema, validation):
        """Registrar resultados de validacion en log"""
        logging.info(f"\n[VALIDACION] Estructura - Esquema: {schema}")
        logging.info(f"{'-'*60}")
        logging.info(f"  Esquema existe: {'OK' if validation['schema_exists'] else 'ERROR'}")
        logging.info(f"  Tablas creadas: {validation['tables_count']}")
        logging.info(f"  Constraints: {validation['constraints_count']}")
        logging.info(f"  Indices totales: {validation['indexes_count']}")
        logging.info(f"  Indices espaciales: {validation['spatial_indexes_count']}")
        logging.info(f"  Tablas de dominio: {validation['domain_tables_count']}")
        logging.info(f"  Metadatos ili2db: {'OK' if validation['metadata_tables'] else 'ERROR'}")
        logging.info(f"{'-'*60}\n")

# ============================================
# FUNCION PRINCIPAL
# ============================================

def main():
    """Funcion principal de ejecucion"""

    print("\n" + "="*70)
    print(" CREACION DE MODELOS FISICOS LADM-COL")
    print(" Agencia Catastral de Cundinamarca")
    print(" Version Windows")
    print("="*70 + "\n")

    # Cargar configuracion
    try:
        config = load_config()
    except Exception as e:
        print(f"ERROR: No se pudo cargar configuracion: {e}")
        sys.exit(1)

    # Configurar logging
    log_dir = os.path.join(config['paths']['base_dir'], config['paths']['log_dir'])
    log_file = setup_logging(log_dir)

    logging.info("="*70)
    logging.info("INICIO DE PROCESO - CREACION DE MODELOS FISICOS")
    logging.info("="*70)
    logging.info(f"Archivo de log: {log_file}")
    logging.info(f"Configuracion cargada desde: {CONFIG_FILE}")

    # Inicializar gestor de base de datos
    db_manager = DatabaseManager(config)

    # Conectar a PostgreSQL (base postgres por defecto)
    if not db_manager.connect(database='postgres'):
        logging.error("[ERROR] No se pudo conectar a PostgreSQL. Abortando proceso.")
        sys.exit(1)

    # Crear base de datos si no existe
    dbname = config['database']['database']
    logging.info(f"\n{'-'*70}")
    logging.info(f"Verificando base de datos: {dbname}")
    logging.info(f"{'-'*70}")

    if not db_manager.create_database(dbname):
        logging.error(f"[ERROR] No se pudo crear base de datos '{dbname}'. Abortando proceso.")
        sys.exit(1)

    # Habilitar extensiones
    if not db_manager.enable_extensions(dbname):
        logging.error("[ERROR] No se pudieron habilitar extensiones. Abortando proceso.")
        sys.exit(1)

    # Inicializar generador de modelos INTERLIS
    model_generator = InterlisModelGenerator(config, db_manager)

    # Validar prerequisitos
    logging.info(f"\n{'-'*70}")
    logging.info("Validando prerequisitos")
    logging.info(f"{'-'*70}")

    if not model_generator.validate_prerequisites():
        logging.error("[ERROR] Faltan prerequisitos. Abortando proceso.")
        sys.exit(1)

    # Procesar cada esquema
    schemas = config['schemas']
    results = []

    logging.info(f"\n{'-'*70}")
    logging.info(f"Procesando {len(schemas)} esquemas")
    logging.info(f"{'-'*70}")

    total_start_time = time.time()

    for i, schema in enumerate(schemas, 1):
        logging.info(f"\n[{i}/{len(schemas)}] Procesando esquema: {schema}")

        result = model_generator.generate_schema(schema, recreate=True)
        results.append(result)

        # Pausa breve entre esquemas
        if i < len(schemas):
            time.sleep(2)

    total_execution_time = time.time() - total_start_time

    # Resumen final
    logging.info(f"\n{'='*70}")
    logging.info("RESUMEN DE EJECUCION")
    logging.info(f"{'='*70}\n")

    successful = [r for r in results if r and r.get('success', False)]
    failed = [r for r in results if r and not r.get('success', False)]

    logging.info(f"[OK] Esquemas creados exitosamente: {len(successful)}/{len(schemas)}")
    logging.info(f"[ERROR] Esquemas con errores: {len(failed)}/{len(schemas)}")
    logging.info(f"[TIEMPO] Tiempo total de ejecucion: {total_execution_time:.2f} segundos")

    if successful:
        logging.info(f"\n{'-'*70}")
        logging.info("Esquemas exitosos:")
        logging.info(f"{'-'*70}")
        for result in successful:
            logging.info(f"  [OK] {result['schema']} - {result['execution_time']:.2f}s")
            if 'validation' in result:
                val = result['validation']
                logging.info(f"    Tablas: {val['tables_count']}, "
                           f"Indices espaciales: {val['spatial_indexes_count']}, "
                           f"Dominios: {val['domain_tables_count']}")

    if failed:
        logging.info(f"\n{'-'*70}")
        logging.info("Esquemas con errores:")
        logging.info(f"{'-'*70}")
        for result in failed:
            logging.info(f"  [ERROR] {result['schema']}")
            if 'error' in result:
                logging.info(f"    Error: {result['error']}")

    # Cerrar conexion
    db_manager.close()

    logging.info(f"\n{'='*70}")
    logging.info("PROCESO FINALIZADO")
    logging.info(f"{'='*70}\n")

    # Codigo de salida
    sys.exit(0 if len(failed) == 0 else 1)

# ============================================
# PUNTO DE ENTRADA
# ============================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("\n\n[AVISO] Proceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logging.error(f"\n\n[ERROR FATAL] {e}", exc_info=True)
        sys.exit(1)
