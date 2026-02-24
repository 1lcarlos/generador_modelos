#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaz Grafica para Generacion de Modelos INTERLIS
Agencia Catastral de Cundinamarca (ACC)

Permite generar modelos fisicos en PostgreSQL/PostGIS
a partir de archivos INTERLIS (.ili) usando ili2pg.

Autor: ACC - Area de Desarrollo
Version: 1.0
Fecha: 2025
"""

import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path

# ============================================
# CONSTANTES Y CONFIGURACION
# ============================================

APP_NAME = "Generador de Modelos INTERLIS"
APP_VERSION = "1.0"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ili2pg_gui")
PROFILES_FILE = os.path.join(CONFIG_DIR, "profiles.json")
LAST_PROFILE_FILE = os.path.join(CONFIG_DIR, "last_profile.json")

# Opciones de ili2pg disponibles
ILI2PG_OPTIONS = {
    "setupPgExt": {"label": "Setup PG Extensions", "description": "Configurar extensiones PostgreSQL", "default": True},
    "coalesceCatalogueRef": {"label": "Coalesce Catalogue Ref", "description": "Unir referencias de catalogo", "default": True},
    "createEnumTabs": {"label": "Create Enum Tables", "description": "Crear tablas de enumeracion", "default": True},
    "createNumChecks": {"label": "Create Num Checks", "description": "Crear validaciones numericas", "default": True},
    "coalesceMultiSurface": {"label": "Coalesce MultiSurface", "description": "Unir multi-superficies", "default": True},
    "coalesceMultiLine": {"label": "Coalesce MultiLine", "description": "Unir multi-lineas", "default": True},
    "coalesceMultiPoint": {"label": "Coalesce MultiPoint", "description": "Unir multi-puntos", "default": True},
    "coalesceArray": {"label": "Coalesce Array", "description": "Unir arrays", "default": True},
    "beautifyEnumDispName": {"label": "Beautify Enum Names", "description": "Embellecer nombres de enumeracion", "default": True},
    "createUnique": {"label": "Create Unique", "description": "Crear constraints unicos", "default": True},
    "createGeomIdx": {"label": "Create Geometry Index", "description": "Crear indices geometricos", "default": True},
    "createFk": {"label": "Create Foreign Keys", "description": "Crear llaves foraneas", "default": True},
    "createFkIdx": {"label": "Create FK Index", "description": "Crear indices de FK", "default": True},
    "createMetaInfo": {"label": "Create Meta Info", "description": "Crear informacion de metadatos", "default": True},
    "expandMultilingual": {"label": "Expand Multilingual", "description": "Expandir campos multilingues", "default": True},
    "createTypeConstraint": {"label": "Create Type Constraint", "description": "Crear constraints de tipo", "default": True},
    "createEnumTabsWithId": {"label": "Enum Tables With ID", "description": "Tablas enum con ID", "default": True},
    "createTidCol": {"label": "Create TID Column", "description": "Crear columna TID", "default": True},
    "smart2Inheritance": {"label": "Smart 2 Inheritance", "description": "Herencia inteligente tipo 2", "default": True},
    "strokeArcs": {"label": "Stroke Arcs", "description": "Convertir arcos a segmentos", "default": True},
}

# ============================================
# CLASE PRINCIPAL DE LA APLICACION
# ============================================

class Ili2pgGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        # Variables
        self.ili_files = []
        self.selected_models = []  # Lista de modelos seleccionados
        self.is_running = False
        self.process = None

        # Crear directorio de configuracion
        os.makedirs(CONFIG_DIR, exist_ok=True)

        # Crear interfaz
        self.create_widgets()

        # Cargar ultima configuracion
        self.load_last_profile()

        # Configurar cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""

        # Frame principal con scroll
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook (pestanas)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestana 1: Configuracion Principal
        self.tab_config = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_config, text="Configuracion")
        self.create_config_tab()

        # Pestana 2: Opciones ili2pg
        self.tab_options = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_options, text="Opciones ili2pg")
        self.create_options_tab()

        # Pestana 3: Ejecucion
        self.tab_execute = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_execute, text="Ejecucion")
        self.create_execute_tab()

        # Barra de estado
        self.status_var = tk.StringVar(value="Listo")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def create_config_tab(self):
        """Crear pestana de configuracion"""

        # Canvas con scroll para contenido largo
        canvas = tk.Canvas(self.tab_config)
        scrollbar = ttk.Scrollbar(self.tab_config, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # ========== SECCION: Perfiles ==========
        profile_frame = ttk.LabelFrame(scrollable_frame, text="Perfiles de Configuracion", padding="10")
        profile_frame.pack(fill=tk.X, pady=(0, 10))

        profile_inner = ttk.Frame(profile_frame)
        profile_inner.pack(fill=tk.X)

        ttk.Label(profile_inner, text="Perfil:").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(profile_inner, width=30, state="readonly")
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)

        ttk.Button(profile_inner, text="Cargar", command=self.load_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_inner, text="Guardar", command=self.save_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_inner, text="Guardar Como...", command=self.save_profile_as).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_inner, text="Eliminar", command=self.delete_profile).pack(side=tk.LEFT, padx=2)

        self.refresh_profiles_list()

        # ========== SECCION: Rutas ==========
        paths_frame = ttk.LabelFrame(scrollable_frame, text="Rutas de Archivos", padding="10")
        paths_frame.pack(fill=tk.X, pady=(0, 10))

        # Ruta ili2pg JAR
        self.create_path_field(paths_frame, "Archivo ili2pg.jar:", "jar_path",
                              "Seleccionar archivo JAR de ili2pg",
                              [("JAR files", "*.jar"), ("All files", "*.*")])

        # Ruta script CTM12
        self.create_path_field(paths_frame, "Script CTM12 (SQL):", "ctm12_path",
                              "Seleccionar script SQL CTM12",
                              [("SQL files", "*.sql"), ("All files", "*.*")])

        # Carpeta de modelos
        self.create_folder_field(paths_frame, "Carpeta de modelos:", "models_folder",
                                "Seleccionar carpeta con archivos .ili")

        # Carpeta de logs
        self.create_folder_field(paths_frame, "Carpeta de logs:", "log_folder",
                                "Seleccionar carpeta para logs")

        # ========== SECCION: Modelos Disponibles ==========
        models_frame = ttk.LabelFrame(scrollable_frame, text="Modelos INTERLIS Disponibles (Seleccion Multiple)", padding="10")
        models_frame.pack(fill=tk.X, pady=(0, 10))

        models_inner = ttk.Frame(models_frame)
        models_inner.pack(fill=tk.X)

        ttk.Button(models_inner, text="Actualizar Lista", command=self.refresh_models_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(models_inner, text="Seleccionar Todos", command=self.select_all_models).pack(side=tk.LEFT, padx=2)
        ttk.Button(models_inner, text="Deseleccionar Todos", command=self.deselect_all_models).pack(side=tk.LEFT, padx=2)

        ttk.Label(models_inner, text="  (Ctrl+Click para seleccion multiple)", foreground="gray").pack(side=tk.LEFT, padx=10)

        # Lista de modelos con seleccion multiple
        models_list_frame = ttk.Frame(models_frame)
        models_list_frame.pack(fill=tk.X, pady=(5, 0))

        self.models_listbox = tk.Listbox(models_list_frame, height=8, selectmode=tk.EXTENDED, exportselection=False)
        models_scrollbar = ttk.Scrollbar(models_list_frame, orient=tk.VERTICAL, command=self.models_listbox.yview)
        self.models_listbox.configure(yscrollcommand=models_scrollbar.set)

        self.models_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        models_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.models_listbox.bind("<<ListboxSelect>>", self.on_model_selected)

        # Modelos seleccionados
        selected_frame = ttk.Frame(models_frame)
        selected_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(selected_frame, text="Modelos seleccionados:", font=("", 9, "bold")).pack(anchor=tk.W)

        self.selected_models_text = tk.Text(selected_frame, height=3, width=50, state=tk.DISABLED,
                                            background="#f0f0f0", foreground="blue")
        self.selected_models_text.pack(fill=tk.X, pady=(2, 0))

        # ========== SECCION: Base de Datos ==========
        db_frame = ttk.LabelFrame(scrollable_frame, text="Conexion a Base de Datos", padding="10")
        db_frame.pack(fill=tk.X, pady=(0, 10))

        # Grid para campos de BD
        db_grid = ttk.Frame(db_frame)
        db_grid.pack(fill=tk.X)

        # Host
        ttk.Label(db_grid, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.db_host = ttk.Entry(db_grid, width=30)
        self.db_host.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self.db_host.insert(0, "localhost")

        # Puerto
        ttk.Label(db_grid, text="Puerto:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.db_port = ttk.Entry(db_grid, width=10)
        self.db_port.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        self.db_port.insert(0, "5432")

        # Base de datos
        ttk.Label(db_grid, text="Base de datos:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_name = ttk.Entry(db_grid, width=30)
        self.db_name.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        # Usuario
        ttk.Label(db_grid, text="Usuario:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.db_user = ttk.Entry(db_grid, width=20)
        self.db_user.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        self.db_user.insert(0, "postgres")

        # Password
        ttk.Label(db_grid, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.db_password = ttk.Entry(db_grid, width=30, show="*")
        self.db_password.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        # Mostrar password
        self.show_pwd_var = tk.BooleanVar()
        ttk.Checkbutton(db_grid, text="Mostrar", variable=self.show_pwd_var,
                       command=self.toggle_password).grid(row=2, column=2, sticky=tk.W, padx=(20, 0))

        # Boton probar conexion
        ttk.Button(db_grid, text="Probar Conexion", command=self.test_connection).grid(row=2, column=3, padx=5)

        # ========== SECCION: Esquemas ==========
        schemas_frame = ttk.LabelFrame(scrollable_frame, text="Esquemas a Crear", padding="10")
        schemas_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(schemas_frame, text="Ingrese los nombres de los esquemas (uno por linea):").pack(anchor=tk.W)

        self.schemas_text = tk.Text(schemas_frame, height=5, width=50)
        self.schemas_text.pack(fill=tk.X, pady=(5, 0))

        schemas_help = ttk.Label(schemas_frame, text="Ejemplo: cun25019, cun25035, cun25436 (cada uno en una linea)",
                                foreground="gray")
        schemas_help.pack(anchor=tk.W)

        # ========== SECCION: SRS ==========
        srs_frame = ttk.LabelFrame(scrollable_frame, text="Sistema de Referencia Espacial", padding="10")
        srs_frame.pack(fill=tk.X, pady=(0, 10))

        srs_inner = ttk.Frame(srs_frame)
        srs_inner.pack(fill=tk.X)

        ttk.Label(srs_inner, text="Codigo EPSG:").pack(side=tk.LEFT)
        self.srs_code = ttk.Entry(srs_inner, width=10)
        self.srs_code.pack(side=tk.LEFT, padx=5)
        self.srs_code.insert(0, "9377")

        ttk.Label(srs_inner, text="(9377 = MAGNA-SIRGAS / CTM12)", foreground="gray").pack(side=tk.LEFT, padx=10)

        # Empaquetar canvas y scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def create_options_tab(self):
        """Crear pestana de opciones ili2pg"""

        # Frame con scroll
        canvas = tk.Canvas(self.tab_options)
        scrollbar = ttk.Scrollbar(self.tab_options, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Titulo
        ttk.Label(scrollable_frame, text="Opciones de ili2pg", font=("", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Botones rapidos
        quick_frame = ttk.Frame(scrollable_frame)
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(quick_frame, text="Seleccionar Todas", command=self.select_all_options).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Deseleccionar Todas", command=self.deselect_all_options).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Restaurar Predeterminadas", command=self.reset_options).pack(side=tk.LEFT, padx=2)

        # Frame para opciones
        options_frame = ttk.LabelFrame(scrollable_frame, text="Opciones Disponibles", padding="10")
        options_frame.pack(fill=tk.BOTH, expand=True)

        # Crear checkboxes para cada opcion
        self.option_vars = {}

        for i, (option_name, option_info) in enumerate(ILI2PG_OPTIONS.items()):
            var = tk.BooleanVar(value=option_info["default"])
            self.option_vars[option_name] = var

            frame = ttk.Frame(options_frame)
            frame.pack(fill=tk.X, pady=2)

            cb = ttk.Checkbutton(frame, text=option_info["label"], variable=var)
            cb.pack(side=tk.LEFT)

            ttk.Label(frame, text=f"  ({option_info['description']})", foreground="gray").pack(side=tk.LEFT)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_execute_tab(self):
        """Crear pestana de ejecucion"""

        # Frame superior - Vista previa y controles
        top_frame = ttk.Frame(self.tab_execute)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Vista previa del comando
        preview_frame = ttk.LabelFrame(top_frame, text="Vista Previa del Comando", padding="10")
        preview_frame.pack(fill=tk.X)

        self.command_preview = scrolledtext.ScrolledText(preview_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.command_preview.pack(fill=tk.X)

        # Botones de control
        control_frame = ttk.Frame(top_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(control_frame, text="Actualizar Vista Previa", command=self.update_command_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Copiar Comando", command=self.copy_command).pack(side=tk.LEFT, padx=2)

        self.execute_btn = ttk.Button(control_frame, text="EJECUTAR", command=self.execute_command,
                                      style="Accent.TButton")
        self.execute_btn.pack(side=tk.RIGHT, padx=2)

        self.stop_btn = ttk.Button(control_frame, text="DETENER", command=self.stop_execution, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=2)

        # Nota sobre comportamiento
        exec_note = ttk.Label(control_frame, text="Si un esquema ya existe, se preguntara que hacer",
                             foreground="gray", font=("", 8))
        exec_note.pack(side=tk.LEFT, padx=20)

        # Frame inferior - Log de ejecucion
        log_frame = ttk.LabelFrame(self.tab_execute, text="Log de Ejecucion", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Tags para colores en el log
        self.log_text.tag_configure("info", foreground="black")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("command", foreground="blue")

        # Botones del log
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(log_buttons, text="Limpiar Log", command=self.clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_buttons, text="Guardar Log", command=self.save_log).pack(side=tk.LEFT, padx=2)

    # ============================================
    # METODOS AUXILIARES PARA CREAR CAMPOS
    # ============================================

    def create_path_field(self, parent, label, attr_name, dialog_title, filetypes):
        """Crear campo de seleccion de archivo"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)

        entry = ttk.Entry(frame, width=60)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        setattr(self, attr_name, entry)

        def browse():
            filename = filedialog.askopenfilename(title=dialog_title, filetypes=filetypes)
            if filename:
                entry.delete(0, tk.END)
                entry.insert(0, filename)
                if attr_name == "models_folder":
                    self.refresh_models_list()

        ttk.Button(frame, text="Examinar...", command=browse).pack(side=tk.LEFT)

    def create_folder_field(self, parent, label, attr_name, dialog_title):
        """Crear campo de seleccion de carpeta"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)

        entry = ttk.Entry(frame, width=60)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        setattr(self, attr_name, entry)

        def browse():
            folder = filedialog.askdirectory(title=dialog_title)
            if folder:
                entry.delete(0, tk.END)
                entry.insert(0, folder)
                if attr_name == "models_folder":
                    self.refresh_models_list()

        ttk.Button(frame, text="Examinar...", command=browse).pack(side=tk.LEFT)

    # ============================================
    # METODOS DE PERFILES
    # ============================================

    def get_profiles(self):
        """Obtener lista de perfiles guardados"""
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_profiles(self, profiles):
        """Guardar perfiles"""
        with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=4, ensure_ascii=False)

    def refresh_profiles_list(self):
        """Actualizar lista de perfiles en el combobox"""
        profiles = self.get_profiles()
        self.profile_combo['values'] = list(profiles.keys())

    def get_current_config(self):
        """Obtener configuracion actual como diccionario"""
        return {
            "jar_path": self.jar_path.get(),
            "ctm12_path": self.ctm12_path.get(),
            "models_folder": self.models_folder.get(),
            "log_folder": self.log_folder.get(),
            "selected_models": self.selected_models,  # Lista de modelos
            "db_host": self.db_host.get(),
            "db_port": self.db_port.get(),
            "db_name": self.db_name.get(),
            "db_user": self.db_user.get(),
            "db_password": self.db_password.get(),
            "schemas": self.schemas_text.get("1.0", tk.END).strip(),
            "srs_code": self.srs_code.get(),
            "options": {name: var.get() for name, var in self.option_vars.items()},
        }

    def set_config(self, config):
        """Aplicar configuracion desde diccionario"""
        def set_entry(entry, value):
            entry.delete(0, tk.END)
            entry.insert(0, value or "")

        set_entry(self.jar_path, config.get("jar_path", ""))
        set_entry(self.ctm12_path, config.get("ctm12_path", ""))
        set_entry(self.models_folder, config.get("models_folder", ""))
        set_entry(self.log_folder, config.get("log_folder", ""))
        set_entry(self.db_host, config.get("db_host", "localhost"))
        set_entry(self.db_port, config.get("db_port", "5432"))
        set_entry(self.db_name, config.get("db_name", ""))
        set_entry(self.db_user, config.get("db_user", "postgres"))
        set_entry(self.db_password, config.get("db_password", ""))
        set_entry(self.srs_code, config.get("srs_code", "9377"))

        self.schemas_text.delete("1.0", tk.END)
        self.schemas_text.insert("1.0", config.get("schemas", ""))

        # Opciones
        options = config.get("options", {})
        for name, var in self.option_vars.items():
            var.set(options.get(name, ILI2PG_OPTIONS[name]["default"]))

        # Actualizar lista de modelos y seleccionar los guardados
        self.refresh_models_list()

        # Restaurar seleccion de modelos
        saved_models = config.get("selected_models", [])
        if saved_models:
            self.models_listbox.select_clear(0, tk.END)
            for i, model in enumerate(self.ili_files):
                if model in saved_models:
                    self.models_listbox.select_set(i)
            self.on_model_selected(None)

    def on_profile_selected(self, event):
        """Evento al seleccionar perfil del combobox"""
        pass  # Solo actualiza la seleccion visual

    def load_profile(self):
        """Cargar perfil seleccionado"""
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showwarning("Aviso", "Seleccione un perfil para cargar")
            return

        profiles = self.get_profiles()
        if profile_name in profiles:
            self.set_config(profiles[profile_name])
            self.status_var.set(f"Perfil '{profile_name}' cargado")
            messagebox.showinfo("Exito", f"Perfil '{profile_name}' cargado correctamente")

    def save_profile(self):
        """Guardar perfil actual"""
        profile_name = self.profile_combo.get()
        if not profile_name:
            self.save_profile_as()
            return

        profiles = self.get_profiles()
        profiles[profile_name] = self.get_current_config()
        self.save_profiles(profiles)
        self.status_var.set(f"Perfil '{profile_name}' guardado")
        messagebox.showinfo("Exito", f"Perfil '{profile_name}' guardado correctamente")

    def save_profile_as(self):
        """Guardar perfil con nuevo nombre"""
        from tkinter import simpledialog
        profile_name = simpledialog.askstring("Guardar Perfil", "Nombre del perfil:")
        if profile_name:
            profiles = self.get_profiles()
            profiles[profile_name] = self.get_current_config()
            self.save_profiles(profiles)
            self.refresh_profiles_list()
            self.profile_combo.set(profile_name)
            self.status_var.set(f"Perfil '{profile_name}' creado")
            messagebox.showinfo("Exito", f"Perfil '{profile_name}' guardado correctamente")

    def delete_profile(self):
        """Eliminar perfil seleccionado"""
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showwarning("Aviso", "Seleccione un perfil para eliminar")
            return

        if messagebox.askyesno("Confirmar", f"Esta seguro de eliminar el perfil '{profile_name}'?"):
            profiles = self.get_profiles()
            if profile_name in profiles:
                del profiles[profile_name]
                self.save_profiles(profiles)
                self.refresh_profiles_list()
                self.profile_combo.set("")
                self.status_var.set(f"Perfil '{profile_name}' eliminado")

    def load_last_profile(self):
        """Cargar ultima configuracion usada"""
        if os.path.exists(LAST_PROFILE_FILE):
            try:
                with open(LAST_PROFILE_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.set_config(config)
            except:
                pass

    def save_last_profile(self):
        """Guardar configuracion actual como ultima usada"""
        try:
            with open(LAST_PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.get_current_config(), f, indent=4, ensure_ascii=False)
        except:
            pass

    # ============================================
    # METODOS DE MODELOS
    # ============================================

    def refresh_models_list(self):
        """Actualizar lista de modelos disponibles"""
        self.models_listbox.delete(0, tk.END)
        self.ili_files = []

        folder = self.models_folder.get()
        if folder and os.path.isdir(folder):
            for file in sorted(os.listdir(folder)):
                if file.endswith('.ili'):
                    self.ili_files.append(file)
                    self.models_listbox.insert(tk.END, file)

        self.status_var.set(f"{len(self.ili_files)} archivos .ili encontrados")

    def on_model_selected(self, event):
        """Evento al seleccionar modelo(s) de la lista"""
        selection = self.models_listbox.curselection()
        self.selected_models = [self.ili_files[i] for i in selection]

        # Actualizar texto de modelos seleccionados
        self.selected_models_text.config(state=tk.NORMAL)
        self.selected_models_text.delete("1.0", tk.END)
        if self.selected_models:
            self.selected_models_text.insert("1.0", "\n".join(self.selected_models))
        else:
            self.selected_models_text.insert("1.0", "(Ninguno seleccionado)")
        self.selected_models_text.config(state=tk.DISABLED)

        self.status_var.set(f"{len(self.selected_models)} modelo(s) seleccionado(s)")

    def select_all_models(self):
        """Seleccionar todos los modelos de la lista"""
        self.models_listbox.select_set(0, tk.END)
        self.on_model_selected(None)

    def deselect_all_models(self):
        """Deseleccionar todos los modelos"""
        self.models_listbox.select_clear(0, tk.END)
        self.on_model_selected(None)

    # ============================================
    # METODOS DE OPCIONES
    # ============================================

    def select_all_options(self):
        """Seleccionar todas las opciones"""
        for var in self.option_vars.values():
            var.set(True)

    def deselect_all_options(self):
        """Deseleccionar todas las opciones"""
        for var in self.option_vars.values():
            var.set(False)

    def reset_options(self):
        """Restaurar opciones predeterminadas"""
        for name, var in self.option_vars.items():
            var.set(ILI2PG_OPTIONS[name]["default"])

    # ============================================
    # METODOS DE BASE DE DATOS
    # ============================================

    def toggle_password(self):
        """Mostrar/ocultar password"""
        if self.show_pwd_var.get():
            self.db_password.config(show="")
        else:
            self.db_password.config(show="*")

    def test_connection(self):
        """Probar conexion a la base de datos"""
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                database="postgres",  # Conectar a postgres por defecto
                user=self.db_user.get(),
                password=self.db_password.get()
            )
            conn.close()

            messagebox.showinfo("Conexion Exitosa",
                              f"Conexion exitosa a PostgreSQL en {self.db_host.get()}:{self.db_port.get()}")
            self.status_var.set("Conexion a BD exitosa")

        except ImportError:
            messagebox.showerror("Error", "Libreria psycopg2 no instalada.\nEjecute: pip install psycopg2-binary")
        except Exception as e:
            messagebox.showerror("Error de Conexion", f"No se pudo conectar a la base de datos:\n{str(e)}")
            self.status_var.set("Error de conexion a BD")

    # ============================================
    # METODOS DE EJECUCION
    # ============================================

    def build_command(self, schema, models_list=None):
        """Construir comando ili2pg para un esquema con multiples modelos"""
        if models_list is None:
            models_list = self.selected_models

        cmd = [
            'java', '-jar', self.jar_path.get(),
            '--schemaimport',
            '--dbhost', self.db_host.get(),
            '--dbport', self.db_port.get(),
            '--dbusr', self.db_user.get(),
            '--dbpwd', self.db_password.get(),
            '--dbdatabase', self.db_name.get(),
            '--dbschema', schema,
            '--defaultSrsCode', self.srs_code.get(),
        ]

        # Agregar directorio de modelos (donde ili2pg buscara los .ili)
        models_folder = self.models_folder.get()
        if models_folder:
            cmd.extend(['--modeldir', models_folder])

        # Agregar prescript CTM12 si existe
        ctm12 = self.ctm12_path.get()
        if ctm12 and os.path.exists(ctm12):
            cmd.extend(['--preScript', ctm12])

        # Agregar opciones habilitadas
        for name, var in self.option_vars.items():
            if var.get():
                cmd.append(f'--{name}')

        # Agregar nombres de modelos (sin extension .ili, separados por punto y coma)
        # ili2pg espera: --models Modelo1;Modelo2;Modelo3
        if models_list:
            model_names = []
            for model in models_list:
                # Quitar extension .ili para obtener el nombre del modelo
                model_name = model.replace('.ili', '') if model.endswith('.ili') else model
                model_names.append(model_name)

            cmd.extend(['--models', ';'.join(model_names)])

        return cmd

    def build_command_display(self, schema):
        """Construir comando para mostrar (sin password)"""
        cmd = self.build_command(schema)
        # Ocultar password
        cmd_display = cmd.copy()
        try:
            pwd_index = cmd_display.index('--dbpwd')
            cmd_display[pwd_index + 1] = '****'
        except ValueError:
            pass
        return ' '.join(cmd_display)

    def update_command_preview(self):
        """Actualizar vista previa del comando"""
        schemas = self.get_schemas_list()

        if not schemas:
            preview = "No hay esquemas definidos"
        elif not self.selected_models:
            preview = "No hay modelo(s) seleccionado(s)"
        else:
            preview = f"# Comando para {len(schemas)} esquema(s) con {len(self.selected_models)} modelo(s)\n"
            preview += f"# Modelos: {', '.join(self.selected_models)}\n\n"
            preview += self.build_command_display(schemas[0])
            if len(schemas) > 1:
                preview += f"\n\n# ... y {len(schemas)-1} esquema(s) mas con los mismos modelos"

        self.command_preview.config(state=tk.NORMAL)
        self.command_preview.delete("1.0", tk.END)
        self.command_preview.insert("1.0", preview)
        self.command_preview.config(state=tk.DISABLED)

    def copy_command(self):
        """Copiar comando al portapapeles"""
        schemas = self.get_schemas_list()
        if schemas and self.selected_model.get():
            command = self.build_command_display(schemas[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(command)
            self.status_var.set("Comando copiado al portapapeles")

    def get_schemas_list(self):
        """Obtener lista de esquemas"""
        text = self.schemas_text.get("1.0", tk.END).strip()
        if not text:
            return []

        schemas = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Soportar comas o lineas separadas
                for schema in line.split(','):
                    schema = schema.strip()
                    if schema:
                        schemas.append(schema)
        return schemas

    def validate_config(self):
        """Validar configuracion antes de ejecutar"""
        errors = []

        if not self.jar_path.get() or not os.path.exists(self.jar_path.get()):
            errors.append("Archivo ili2pg.jar no especificado o no existe")

        if not self.models_folder.get() or not os.path.isdir(self.models_folder.get()):
            errors.append("Carpeta de modelos no especificada o no existe")

        if not self.selected_models:
            errors.append("No hay modelo(s) INTERLIS seleccionado(s)")

        if not self.db_host.get():
            errors.append("Host de base de datos no especificado")

        if not self.db_name.get():
            errors.append("Nombre de base de datos no especificado")

        if not self.db_user.get():
            errors.append("Usuario de base de datos no especificado")

        if not self.get_schemas_list():
            errors.append("No hay esquemas definidos")

        return errors

    def log_message(self, message, tag="info"):
        """Agregar mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """Limpiar log"""
        self.log_text.delete("1.0", tk.END)

    def save_log(self):
        """Guardar log a archivo"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfilename=f"ili2pg_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get("1.0", tk.END))
            self.status_var.set(f"Log guardado: {filename}")

    def execute_command(self):
        """Ejecutar creacion de modelos"""
        # Validar
        errors = self.validate_config()
        if errors:
            messagebox.showerror("Errores de Configuracion", "\n".join(errors))
            return

        # Confirmar
        schemas = self.get_schemas_list()
        models_str = "\n".join([f"  - {m}" for m in self.selected_models[:5]])
        if len(self.selected_models) > 5:
            models_str += f"\n  ... y {len(self.selected_models)-5} mas"

        schemas_str = "\n".join([f"  - {s}" for s in schemas[:5]])
        if len(schemas) > 5:
            schemas_str += f"\n  ... y {len(schemas)-5} mas"

        confirm_msg = f"RESUMEN DE EJECUCION\n\n"
        confirm_msg += f"Modelos a importar ({len(self.selected_models)}):\n{models_str}\n\n"
        confirm_msg += f"Esquemas a crear ({len(schemas)}):\n{schemas_str}\n\n"
        confirm_msg += "Continuar?"

        if not messagebox.askyesno("Confirmar Ejecucion", confirm_msg):
            return

        # Iniciar ejecucion en hilo separado
        self.is_running = True
        self.execute_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        thread = threading.Thread(target=self.execute_schemas, args=(schemas,))
        thread.daemon = True
        thread.start()

    def ask_schema_action(self, schema):
        """Preguntar al usuario que hacer con un esquema existente"""
        # Esta funcion se llama desde el hilo principal
        result = [None]  # Usar lista para poder modificar desde la funcion interna

        def ask():
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Esquema Existente: {schema}")
            dialog.geometry("450x200")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()

            # Centrar ventana
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
            y = (dialog.winfo_screenheight() // 2) - (200 // 2)
            dialog.geometry(f"+{x}+{y}")

            ttk.Label(dialog, text=f"El esquema '{schema}' ya existe.",
                     font=("", 11, "bold")).pack(pady=(20, 10))
            ttk.Label(dialog, text="Que desea hacer?").pack(pady=(0, 20))

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            def set_result(value):
                result[0] = value
                dialog.destroy()

            ttk.Button(btn_frame, text="RECREAR\n(Borrar todo y crear nuevo)",
                      command=lambda: set_result("recreate"), width=20).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="ACTUALIZAR\n(Agregar modelos)",
                      command=lambda: set_result("update"), width=20).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="OMITIR\n(No procesar)",
                      command=lambda: set_result("skip"), width=20).pack(side=tk.LEFT, padx=5)

            # Checkbox para aplicar a todos
            self.apply_to_all_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(dialog, text="Aplicar esta decision a todos los esquemas existentes",
                           variable=self.apply_to_all_var).pack(pady=(15, 10))

            dialog.protocol("WM_DELETE_WINDOW", lambda: set_result("cancel"))
            dialog.wait_window()

        self.root.after(0, ask)

        # Esperar respuesta
        while result[0] is None:
            import time
            time.sleep(0.1)

        return result[0], getattr(self, 'apply_to_all_var', tk.BooleanVar()).get()

    def execute_schemas(self, schemas):
        """Ejecutar creacion de esquemas (en hilo separado)"""
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        self.log_message("="*60, "info")
        self.log_message("INICIO DE PROCESO - CREACION DE MODELOS INTERLIS", "info")
        self.log_message("="*60, "info")
        self.log_message(f"Modelos: {', '.join(self.selected_models)}", "info")
        self.log_message(f"Esquemas: {len(schemas)}", "info")
        self.log_message("", "info")

        successful = 0
        failed = 0
        skipped = 0
        default_action = None  # Para "aplicar a todos"

        try:
            # Conectar a PostgreSQL
            self.log_message("Conectando a PostgreSQL...", "info")
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                database="postgres",
                user=self.db_user.get(),
                password=self.db_password.get()
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            # Verificar/crear base de datos
            db_name = self.db_name.get()
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cur.fetchone():
                self.log_message(f"Creando base de datos '{db_name}'...", "info")
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                self.log_message(f"Base de datos '{db_name}' creada", "success")
            else:
                self.log_message(f"Base de datos '{db_name}' ya existe", "info")

            cur.close()
            conn.close()

            # Conectar a la base de datos destino
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                database=db_name,
                user=self.db_user.get(),
                password=self.db_password.get()
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            # Habilitar extensiones
            self.log_message("Habilitando extensiones...", "info")
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            self.log_message("Extensiones PostGIS y uuid-ossp habilitadas", "success")

            # Procesar cada esquema
            for i, schema in enumerate(schemas, 1):
                if not self.is_running:
                    self.log_message("Proceso detenido por el usuario", "warning")
                    break

                self.log_message("", "info")
                self.log_message(f"[{i}/{len(schemas)}] Procesando esquema: {schema}", "info")
                self.log_message("-"*40, "info")
                self.status_var.set(f"Procesando {schema} ({i}/{len(schemas)})")

                try:
                    # Verificar si el esquema existe
                    cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (schema,))
                    schema_exists = cur.fetchone() is not None

                    action = "create"  # Por defecto, crear

                    if schema_exists:
                        if default_action:
                            action = default_action
                            self.log_message(f"Esquema existe - aplicando accion predefinida: {action}", "info")
                        else:
                            # Preguntar al usuario
                            self.log_message(f"Esquema '{schema}' ya existe - esperando decision del usuario...", "warning")
                            action, apply_to_all = self.ask_schema_action(schema)

                            if action == "cancel":
                                self.log_message("Proceso cancelado por el usuario", "warning")
                                break

                            if apply_to_all:
                                default_action = action
                                self.log_message(f"Aplicando '{action}' a todos los esquemas existentes", "info")

                    # Ejecutar segun la accion
                    if action == "skip":
                        self.log_message(f"Esquema '{schema}' omitido", "warning")
                        skipped += 1
                        continue

                    if action == "recreate":
                        self.log_message(f"Eliminando esquema existente '{schema}'...", "warning")
                        cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
                        cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(f"{schema}_mi")))
                        self.log_message(f"Esquema '{schema}' eliminado", "info")

                    # action == "update" o "create" -> ejecutar ili2pg
                    # ili2pg maneja la actualizacion/creacion automaticamente

                    # Construir y ejecutar comando
                    cmd = self.build_command(schema)
                    self.log_message(f"Ejecutando ili2pg con {len(self.selected_models)} modelo(s)...", "command")

                    # Crear archivo de log para ili2pg
                    log_folder = self.log_folder.get()
                    if log_folder:
                        os.makedirs(log_folder, exist_ok=True)
                        log_file = os.path.join(log_folder, f"ili2pg_{schema}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                        cmd.extend(['--log', log_file])

                    self.process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        shell=True
                    )

                    # Leer salida
                    for line in self.process.stdout:
                        line = line.strip()
                        if line:
                            if "error" in line.lower():
                                self.log_message(f"  {line}", "error")
                            elif "warning" in line.lower():
                                self.log_message(f"  {line}", "warning")
                            else:
                                self.log_message(f"  {line}", "info")

                    self.process.wait()

                    if self.process.returncode == 0:
                        self.log_message(f"Esquema '{schema}' procesado exitosamente", "success")
                        successful += 1
                    else:
                        self.log_message(f"Error procesando esquema '{schema}' (codigo: {self.process.returncode})", "error")
                        failed += 1

                except Exception as e:
                    self.log_message(f"Error procesando '{schema}': {str(e)}", "error")
                    failed += 1

            cur.close()
            conn.close()

        except Exception as e:
            self.log_message(f"Error general: {str(e)}", "error")

        # Resumen
        self.log_message("", "info")
        self.log_message("="*60, "info")
        self.log_message("RESUMEN DE EJECUCION", "info")
        self.log_message("="*60, "info")
        self.log_message(f"Esquemas exitosos: {successful}", "success" if successful > 0 else "info")
        self.log_message(f"Esquemas con errores: {failed}", "error" if failed > 0 else "info")
        self.log_message(f"Esquemas omitidos: {skipped}", "warning" if skipped > 0 else "info")
        self.log_message("="*60, "info")

        # Restaurar estado
        self.is_running = False
        self.process = None
        self.root.after(0, self.restore_buttons)
        self.root.after(0, lambda: self.status_var.set(f"Completado: {successful} exitosos, {failed} errores, {skipped} omitidos"))

    def restore_buttons(self):
        """Restaurar estado de botones"""
        self.execute_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def stop_execution(self):
        """Detener ejecucion"""
        if messagebox.askyesno("Confirmar", "Detener la ejecucion?"):
            self.is_running = False
            if self.process:
                self.process.terminate()
            self.log_message("Deteniendo proceso...", "warning")

    # ============================================
    # METODOS DE CIERRE
    # ============================================

    def on_closing(self):
        """Evento al cerrar la ventana"""
        if self.is_running:
            if not messagebox.askyesno("Confirmar", "Hay un proceso en ejecucion. Salir de todas formas?"):
                return
            self.is_running = False
            if self.process:
                self.process.terminate()

        # Guardar configuracion actual
        self.save_last_profile()
        self.root.destroy()


# ============================================
# PUNTO DE ENTRADA
# ============================================

def main():
    root = tk.Tk()

    # Estilo
    style = ttk.Style()
    if sys.platform == "win32":
        style.theme_use("vista")

    # Crear aplicacion
    app = Ili2pgGUI(root)

    # Iniciar loop
    root.mainloop()


if __name__ == "__main__":
    main()
