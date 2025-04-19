import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from collections import defaultdict
from datetime import datetime, date
import ctypes  # Para manejar el escalado de DPI en Windows
import os  # Para verificar el sistema operativo

# Importar los componentes modulares
from date_selector import DateSelector
from email_preview import EmailPreview
from exporter import Exporter

# Importar tus funciones reales
from campaign_logic import obtener_campanas, mostrar_campanas_en_tabla, seleccionar_campanas, query_metric_aggregates_post
from utils import format_number, format_percentage

# Habilitar el escalado de DPI en Windows
if os.name == 'nt':  # Solo en Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Hacer que la aplicación sea consciente del DPI
    except Exception as e:
        print(f"No se pudo establecer la conciencia de DPI: {e}")

class ResultadosApp:
    def __init__(self, root, campanas, list_start_date, list_end_date):
        self.root = root
        self.campanas = campanas
        self.list_start_date = list_start_date
        self.list_end_date = list_end_date
        self.last_results = {}
        self.show_local_value = tk.BooleanVar(value=True)
        self.webview_window = None
        self.is_analysis_mode = False  # Controla si estamos mostrando el panel de resultados
        self.template_ids = {}  # Diccionario para almacenar los template_id
        self.resultados_tabla = None  # Inicializar como None
        self.resultados_label = None  # Inicializar como None

        self.root.title(f"Resultados de Campañas ({list_start_date} a {list_end_date})")
        self.root.after_ids = []

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.root.update()
        self.original_width = self.screen_width
        self.original_height = self.screen_height
        self.root.state('zoomed')

        # Crear la instancia de EmailPreview
        self.email_preview = EmailPreview(
            self.webview_window,
            None,  # campanas_tabla, se asignará después
            self.template_ids,
            self.is_analysis_mode,
            self.resultados_tabla,
            self.resultados_label,
            self.screen_width,
            self.screen_height,
            self.root
        )

        # Crear la instancia de Exporter
        self.exporter = Exporter(
            self.campanas,
            None,  # campanas_tabla, se asignará después
            self.grouping_var if hasattr(self, 'grouping_var') else tk.StringVar(value="País"),
            self.last_results,
            self.is_analysis_mode,
            self.resultados_tabla
        )

        # Hacer la ventana principal responsive
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Frame principal que contendrá todo
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)  # La fila del Treeview será la que se expanda

        # Frame para centrar el campo de entrada
        self.entry_frame = tk.Frame(self.main_frame)
        self.entry_frame.grid(row=2, column=0, pady=5)
        tk.Label(self.entry_frame, text="Ingrese códigos de país, palabras clave o números de campaña (separados por coma):", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack()
        self.entry = tk.Entry(self.entry_frame, width=50)
        self.entry.pack(pady=5)
        self.entry.bind("<Return>", lambda event: self.analizar())

        # Frame para centrar los botones
        self.buttons_frame = tk.Frame(self.main_frame)
        self.buttons_frame.grid(row=3, column=0, pady=10)
        self.frame_botones = tk.Frame(self.buttons_frame)
        self.frame_botones.pack()
        self.btn_analizar = tk.Button(self.frame_botones, text="Analizar", command=self.analizar, 
                                     bg="#23376D", fg="white", activebackground="#3A4F9A", 
                                     activeforeground="white", font=("TkDefaultFont", 10, "bold"))
        self.btn_analizar.pack(side=tk.LEFT, padx=5)
        # Habilitar el botón Exportar desde el inicio si hay campañas
        self.btn_exportar = tk.Button(self.frame_botones, text="Exportar", command=self.exporter.exportar, 
                                     bg="#23376D" if self.campanas else "#A9A9A9", 
                                     fg="white", activebackground="#3A4F9A", 
                                     activeforeground="white", font=("TkDefaultFont", 10, "bold"), 
                                     state=tk.NORMAL if self.campanas else tk.DISABLED)
        self.btn_exportar.pack(side=tk.LEFT, padx=5)
        self.btn_nuevo_rango = tk.Button(self.frame_botones, text="Nuevo Rango", command=self.nuevo_rango, 
                                        bg="#23376D", fg="white", activebackground="#3A4F9A", 
                                        activeforeground="white", font=("TkDefaultFont", 10, "bold"))
        self.btn_nuevo_rango.pack(side=tk.LEFT, padx=5)

        # Configurar la vista inicial con solo la tabla de métricas
        self.setup_metrics_view()

        self.root.update()
        self.root.lift()
        self.root.focus_set()
        self.root.after(100, self.entry.focus_set)

    def setup_metrics_view(self):
        """Configura la vista inicial con solo la tabla de métricas."""
        # Limpiar el frame principal, pero preservar el campo de entrada y los botones
        for widget in self.main_frame.winfo_children():
            if widget not in (self.entry_frame, self.buttons_frame):
                widget.destroy()

        # Frame izquierdo que contendrá la tabla de métricas
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(2, weight=1)  # La fila del Treeview será la que se expanda

        # Frame de controles (Agrupar por, Mostrar Total Value)
        control_frame = tk.Frame(self.left_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=5)

        tk.Label(control_frame, text="Agrupar por:", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.grouping_var = tk.StringVar(value="País")
        grouping_options = ttk.Combobox(control_frame, textvariable=self.grouping_var, values=["País", "Fecha"], state="readonly")
        grouping_options.pack(side=tk.LEFT, padx=5)
        grouping_options.bind("<<ComboboxSelected>>", self.update_grouping)

        tk.Checkbutton(control_frame, text="Mostrar Total Value (Local)", variable=self.show_local_value, 
                       command=self.toggle_local_value, fg="#23376D").pack(side=tk.LEFT, padx=5)

        tk.Label(self.left_frame, text="Campañas en el rango seleccionado:", fg="#23376D", font=("TkDefaultFont", 12, "bold")).grid(row=1, column=0, sticky="ew", pady=5)

        # Frame para el Treeview con scrollbar
        treeview_frame = tk.Frame(self.left_frame)
        treeview_frame.grid(row=2, column=0, sticky="nsew")
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        # Crear el Treeview sin altura fija
        self.campanas_tabla = ttk.Treeview(treeview_frame, columns=(
            "Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OrderUnique", 
            "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "Subject", "Preview"
        ), show="headings")
        self.campanas_tabla.grid(row=0, column=0, sticky="nsew")

        # Añadir scrollbar vertical
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.campanas_tabla.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.campanas_tabla.configure(yscrollcommand=scrollbar.set)

        # Configurar encabezados y estilos
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10), rowheight=30)  # Aumentar la altura de las filas
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        self.campanas_tabla.heading("Numero", text="#")
        self.campanas_tabla.heading("Nombre", text="Nombre")
        self.campanas_tabla.heading("FechaEnvio", text="Fecha de Envío")
        self.campanas_tabla.heading("OpenRate", text="Open Rate")
        self.campanas_tabla.heading("ClickRate", text="Click Rate")
        self.campanas_tabla.heading("Recibios", text="Recibidos")
        self.campanas_tabla.heading("OrderUnique", text="Unique Orders")
        self.campanas_tabla.heading("OrderSumValue", text="Total Value (USD)")
        self.campanas_tabla.heading("OrderSumValueLocal", text="Total Value (Local)")
        self.campanas_tabla.heading("PerRecipient", text="Per Recipient")
        self.campanas_tabla.heading("OrderCount", text="Order Count")
        self.campanas_tabla.heading("Subject", text="Subject Line")
        self.campanas_tabla.heading("Preview", text="Preview Text")

        # Calcular anchos de columnas (usamos el 90% del ancho de la pantalla)
        total_table_width = int(self.screen_width * 0.9)
        column_widths = {
            "Numero": int(total_table_width * 0.03),
            "Nombre": int(total_table_width * 0.08),
            "FechaEnvio": int(total_table_width * 0.06),
            "OpenRate": int(total_table_width * 0.05),
            "ClickRate": int(total_table_width * 0.05),
            "Recibios": int(total_table_width * 0.06),
            "OrderUnique": int(total_table_width * 0.05),
            "OrderSumValue": int(total_table_width * 0.08),
            "OrderSumValueLocal": int(total_table_width * 0.08),
            "PerRecipient": int(total_table_width * 0.08),
            "OrderCount": int(total_table_width * 0.05),
            "Subject": int(total_table_width * 0.12),
            "Preview": int(total_table_width * 0.12),
        }

        self.column_widths = column_widths  # Guardar para usar después

        self.campanas_tabla.column("Numero", width=column_widths["Numero"], anchor="center")
        self.campanas_tabla.column("Nombre", width=column_widths["Nombre"])
        self.campanas_tabla.column("FechaEnvio", width=column_widths["FechaEnvio"])
        self.campanas_tabla.column("OpenRate", width=column_widths["OpenRate"], anchor="center")
        self.campanas_tabla.column("ClickRate", width=column_widths["ClickRate"], anchor="center")
        self.campanas_tabla.column("Recibios", width=column_widths["Recibios"], anchor="center")
        self.campanas_tabla.column("OrderUnique", width=column_widths["OrderUnique"], anchor="center")
        self.campanas_tabla.column("OrderSumValue", width=column_widths["OrderSumValue"], anchor="e")
        self.campanas_tabla.column("OrderSumValueLocal", width=column_widths["OrderSumValueLocal"], anchor="e")
        self.campanas_tabla.column("PerRecipient", width=column_widths["PerRecipient"], anchor="e")
        self.campanas_tabla.column("OrderCount", width=column_widths["OrderCount"], anchor="center")
        self.campanas_tabla.column("Subject", width=column_widths["Subject"])
        self.campanas_tabla.column("Preview", width=column_widths["Preview"])

        self.campanas_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")
        self.campanas_tabla.bind("<Double-1>", self.email_preview.preview_template)
        self.email_preview.campanas_tabla = self.campanas_tabla  # Asignar después de crear la tabla
        self.exporter.campanas_tabla = self.campanas_tabla  # Asignar después de crear la tabla

        # Crear el Treeview para el Total General
        self.grand_total_tabla = ttk.Treeview(self.left_frame, columns=(
            "Numero", "Nombre", "OpenRate", "ClickRate", "Recibios", "OrderUnique", 
            "OrderSumValue", "PerRecipient", "OrderCount"
        ), show="headings", height=1)
        self.grand_total_tabla.grid(row=3, column=0, sticky="ew", pady=5)

        self.grand_total_tabla.heading("Numero", text="#")
        self.grand_total_tabla.heading("Nombre", text="Nombre")
        self.grand_total_tabla.heading("OpenRate", text="Open Rate")
        self.grand_total_tabla.heading("ClickRate", text="Click Rate")
        self.grand_total_tabla.heading("Recibios", text="Recibidos")
        self.grand_total_tabla.heading("OrderUnique", text="Unique Orders")
        self.grand_total_tabla.heading("OrderSumValue", text="Total Value (USD)")
        self.grand_total_tabla.heading("PerRecipient", text="Per Recipient")
        self.grand_total_tabla.heading("OrderCount", text="Order Count")

        self.grand_total_tabla.column("Numero", width=column_widths["Numero"], anchor="center")
        self.grand_total_tabla.column("Nombre", width=column_widths["Nombre"])
        self.grand_total_tabla.column("OpenRate", width=column_widths["OpenRate"], anchor="center")
        self.grand_total_tabla.column("ClickRate", width=column_widths["ClickRate"], anchor="center")
        self.grand_total_tabla.column("Recibios", width=column_widths["Recibios"], anchor="center")
        self.grand_total_tabla.column("OrderUnique", width=column_widths["OrderUnique"], anchor="center")
        self.grand_total_tabla.column("OrderSumValue", width=column_widths["OrderSumValue"], anchor="e")
        self.grand_total_tabla.column("PerRecipient", width=column_widths["PerRecipient"], anchor="e")
        self.grand_total_tabla.column("OrderCount", width=column_widths["OrderCount"], anchor="center")

        self.grand_total_tabla.tag_configure("grand_total", font=("Arial", 11, "bold"), background="#23376D", foreground="white")

        # Actualizar grouping_var en Exporter después de crearlo
        self.exporter.grouping_var = self.grouping_var

        self.update_grouping(None)

    def setup_analysis_view(self):
        """Configura la vista con dos paneles: métricas a la izquierda y resultados a la derecha."""
        self.is_analysis_mode = True
        self.email_preview.is_analysis_mode = self.is_analysis_mode  # Actualizar en EmailPreview
        self.exporter.is_analysis_mode = self.is_analysis_mode  # Actualizar en Exporter

        # Limpiar el frame principal, pero preservar el campo de entrada y los botones
        for widget in self.main_frame.winfo_children():
            if widget not in (self.entry_frame, self.buttons_frame):
                widget.destroy()

        # Crear un PanedWindow para dividir la ventana en dos
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.grid(row=1, column=0, sticky="nsew")
        self.main_frame.rowconfigure(1, weight=1)  # Asegurar que el PanedWindow se expanda

        # Frame izquierdo (métricas)
        self.left_frame = tk.Frame(self.paned)
        self.paned.add(self.left_frame, weight=1)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.rowconfigure(2, weight=1)

        control_frame = tk.Frame(self.left_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=5)

        tk.Label(control_frame, text="Agrupar por:", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)
        grouping_options = ttk.Combobox(control_frame, textvariable=self.grouping_var, values=["País", "Fecha"], state="readonly")
        grouping_options.pack(side=tk.LEFT, padx=5)
        grouping_options.bind("<<ComboboxSelected>>", self.update_grouping)

        tk.Checkbutton(control_frame, text="Mostrar Total Value (Local)", variable=self.show_local_value, 
                       command=self.toggle_local_value, fg="#23376D").pack(side=tk.LEFT, padx=5)

        tk.Label(self.left_frame, text="Campañas en el rango seleccionado:", fg="#23376D", font=("TkDefaultFont", 12, "bold")).grid(row=1, column=0, sticky="ew", pady=5)

        # Frame para el Treeview con scrollbar
        treeview_frame = tk.Frame(self.left_frame)
        treeview_frame.grid(row=2, column=0, sticky="nsew")
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        self.campanas_tabla = ttk.Treeview(treeview_frame, columns=(
            "Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OrderUnique", 
            "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "Subject", "Preview"
        ), show="headings")
        self.campanas_tabla.grid(row=0, column=0, sticky="nsew")

        # Añadir scrollbar vertical
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.campanas_tabla.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.campanas_tabla.configure(yscrollcommand=scrollbar.set)

        # Configurar estilos
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        self.campanas_tabla.heading("Numero", text="#")
        self.campanas_tabla.heading("Nombre", text="Nombre")
        self.campanas_tabla.heading("FechaEnvio", text="Fecha de Envío")
        self.campanas_tabla.heading("OpenRate", text="Open Rate")
        self.campanas_tabla.heading("ClickRate", text="Click Rate")
        self.campanas_tabla.heading("Recibios", text="Recibidos")
        self.campanas_tabla.heading("OrderUnique", text="Unique Orders")
        self.campanas_tabla.heading("OrderSumValue", text="Total Value (USD)")
        self.campanas_tabla.heading("OrderSumValueLocal", text="Total Value (Local)")
        self.campanas_tabla.heading("PerRecipient", text="Per Recipient")
        self.campanas_tabla.heading("OrderCount", text="Order Count")
        self.campanas_tabla.heading("Subject", text="Subject Line")
        self.campanas_tabla.heading("Preview", text="Preview Text")

        # Usar anchos más ajustados ya que ahora compartimos la ventana
        total_table_width = int(self.screen_width * 0.5)
        column_widths = {
            "Numero": int(total_table_width * 0.03),
            "Nombre": int(total_table_width * 0.08),
            "FechaEnvio": int(total_table_width * 0.06),
            "OpenRate": int(total_table_width * 0.05),
            "ClickRate": int(total_table_width * 0.05),
            "Recibios": int(total_table_width * 0.06),
            "OrderUnique": int(total_table_width * 0.05),
            "OrderSumValue": int(total_table_width * 0.08),
            "OrderSumValueLocal": int(total_table_width * 0.08),
            "PerRecipient": int(total_table_width * 0.08),
            "OrderCount": int(total_table_width * 0.05),
            "Subject": int(total_table_width * 0.12),
            "Preview": int(total_table_width * 0.12),
        }

        self.column_widths = column_widths  # Actualizar los anchos para el modo análisis

        self.campanas_tabla.column("Numero", width=column_widths["Numero"], anchor="center")
        self.campanas_tabla.column("Nombre", width=column_widths["Nombre"])
        self.campanas_tabla.column("FechaEnvio", width=column_widths["FechaEnvio"])
        self.campanas_tabla.column("OpenRate", width=column_widths["OpenRate"], anchor="center")
        self.campanas_tabla.column("ClickRate", width=column_widths["ClickRate"], anchor="center")
        self.campanas_tabla.column("Recibios", width=column_widths["Recibios"], anchor="center")
        self.campanas_tabla.column("OrderUnique", width=column_widths["OrderUnique"], anchor="center")
        self.campanas_tabla.column("OrderSumValue", width=column_widths["OrderSumValue"], anchor="e")
        self.campanas_tabla.column("OrderSumValueLocal", width=column_widths["OrderSumValueLocal"], anchor="e")
        self.campanas_tabla.column("PerRecipient", width=column_widths["PerRecipient"], anchor="e")
        self.campanas_tabla.column("OrderCount", width=column_widths["OrderCount"], anchor="center")
        self.campanas_tabla.column("Subject", width=column_widths["Subject"])
        self.campanas_tabla.column("Preview", width=column_widths["Preview"])

        self.campanas_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")
        self.campanas_tabla.bind("<Double-1>", self.email_preview.preview_template)
        self.email_preview.campanas_tabla = self.campanas_tabla  # Actualizar después de crear la tabla
        self.exporter.campanas_tabla = self.campanas_tabla  # Actualizar después de crear la tabla

        self.grand_total_tabla = ttk.Treeview(self.left_frame, columns=(
            "Numero", "Nombre", "OpenRate", "ClickRate", "Recibios", "OrderUnique", 
            "OrderSumValue", "PerRecipient", "OrderCount"
        ), show="headings", height=1)
        self.grand_total_tabla.grid(row=3, column=0, sticky="ew", pady=5)

        self.grand_total_tabla.heading("Numero", text="#")
        self.grand_total_tabla.heading("Nombre", text="Nombre")
        self.grand_total_tabla.heading("OpenRate", text="Open Rate")
        self.grand_total_tabla.heading("ClickRate", text="Click Rate")
        self.grand_total_tabla.heading("Recibios", text="Recibidos")
        self.grand_total_tabla.heading("OrderUnique", text="Unique Orders")
        self.grand_total_tabla.heading("OrderSumValue", text="Total Value (USD)")
        self.grand_total_tabla.heading("PerRecipient", text="Per Recipient")
        self.grand_total_tabla.heading("OrderCount", text="Order Count")

        self.grand_total_tabla.column("Numero", width=column_widths["Numero"], anchor="center")
        self.grand_total_tabla.column("Nombre", width=column_widths["Nombre"])
        self.grand_total_tabla.column("OpenRate", width=column_widths["OpenRate"], anchor="center")
        self.grand_total_tabla.column("ClickRate", width=column_widths["ClickRate"], anchor="center")
        self.grand_total_tabla.column("Recibios", width=column_widths["Recibios"], anchor="center")
        self.grand_total_tabla.column("OrderUnique", width=column_widths["OrderUnique"], anchor="center")
        self.grand_total_tabla.column("OrderSumValue", width=column_widths["OrderSumValue"], anchor="e")
        self.grand_total_tabla.column("PerRecipient", width=column_widths["PerRecipient"], anchor="e")
        self.grand_total_tabla.column("OrderCount", width=column_widths["OrderCount"], anchor="center")

        self.grand_total_tabla.tag_configure("grand_total", font=("Arial", 11, "bold"), background="#23376D", foreground="white")

        # Frame derecho (resultados)
        self.right_frame = tk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=1)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(1, weight=1)

        # Frame para el título y el botón de cerrar
        self.results_header_frame = tk.Frame(self.right_frame)
        self.results_header_frame.grid(row=0, column=0, sticky="ew", pady=5)

        self.resultados_label = tk.Label(self.results_header_frame, text="Resultados del análisis:", font=("TkDefaultFont", 12, "bold"), fg="#23376D")
        self.resultados_label.pack(side=tk.LEFT, padx=5)
        self.email_preview.resultados_label = self.resultados_label  # Actualizar en EmailPreview

        # Botón para cerrar el panel de análisis
        self.btn_cerrar_analisis = tk.Button(self.results_header_frame, text="Cerrar Análisis", command=self.cerrar_analisis, 
                                             bg="#A9A9A9", fg="white", activebackground="#3A4F9A", 
                                             activeforeground="white", font=("TkDefaultFont", 10, "bold"))
        self.btn_cerrar_analisis.pack(side=tk.RIGHT, padx=5)

        # Frame para el Treeview de resultados con scrollbar
        content_frame = tk.Frame(self.right_frame)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        self.resultados_tabla = ttk.Treeview(content_frame, columns=("Campaign", "Clics Totales", "URL", "Clics Totales URL", "Clics Únicos"), show="headings")
        self.resultados_tabla.grid(row=0, column=0, sticky="nsew")
        self.email_preview.resultados_tabla = self.resultados_tabla  # Actualizar en EmailPreview
        self.exporter.resultados_tabla = self.resultados_tabla  # Actualizar en Exporter

        # Añadir scrollbar vertical para resultados
        resultados_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.resultados_tabla.yview)
        resultados_scrollbar.grid(row=0, column=1, sticky="ns")
        self.resultados_tabla.configure(yscrollcommand=resultados_scrollbar.set)

        self.resultados_tabla.heading("Campaign", text="Campaña")
        self.resultados_tabla.heading("Clics Totales", text="Clics Totales")
        self.resultados_tabla.heading("URL", text="URL")
        self.resultados_tabla.heading("Clics Totales URL", text="Clics Totales URL")
        self.resultados_tabla.heading("Clics Únicos", text="Clics Únicos")

        total_resultados_width = int(self.screen_width * 0.5)
        self.resultados_tabla.column("Campaign", width=int(total_resultados_width * 0.15), anchor="w")
        self.resultados_tabla.column("Clics Totales", width=int(total_resultados_width * 0.15), anchor="center")
        self.resultados_tabla.column("URL", width=int(total_resultados_width * 0.40), anchor="w")
        self.resultados_tabla.column("Clics Totales URL", width=int(total_resultados_width * 0.15), anchor="center")
        self.resultados_tabla.column("Clics Únicos", width=int(total_resultados_width * 0.15), anchor="center")

        self.resultados_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")

        # Actualizar la tabla de métricas
        self.update_grouping(None)

    def cerrar_analisis(self):
        """Cierra el panel de análisis y restaura la vista de métricas."""
        self.is_analysis_mode = False
        self.email_preview.is_analysis_mode = self.is_analysis_mode  # Actualizar en EmailPreview
        self.exporter.is_analysis_mode = self.is_analysis_mode  # Actualizar en Exporter
        self.last_results.clear()  # Limpiar los resultados del análisis
        self.resultados_tabla = None
        self.email_preview.resultados_tabla = None  # Resetear en EmailPreview
        self.exporter.resultados_tabla = None  # Resetear en Exporter
        self.resultados_label = None
        self.email_preview.resultados_label = None  # Resetear en EmailPreview
        self.setup_metrics_view()

        self.root.update()
        self.entry.focus_set()

    def toggle_local_value(self):
        show = self.show_local_value.get()
        column_width = self.column_widths["OrderSumValueLocal"]
        if show:
            self.campanas_tabla.column("OrderSumValueLocal", width=column_width, anchor="e")
            self.campanas_tabla.column("OrderSumValueLocal", stretch=tk.YES)
        else:
            self.campanas_tabla.column("OrderSumValueLocal", width=0, anchor="e", stretch=tk.NO)
        self.update_grouping(None)

    def update_grouping(self, event):
        # Limpiar el diccionario de template_ids antes de actualizar la tabla
        self.template_ids.clear()
        
        try:
            # Llamar a mostrar_campanas_en_tabla y pasar self.template_ids para que lo llene
            all_subtotals = mostrar_campanas_en_tabla(
                self.campanas, 
                self.campanas_tabla, 
                self.grouping_var.get(), 
                self.show_local_value.get(),
                template_ids_dict=self.template_ids  # Pasar el diccionario para almacenar los template_id
            )
        except Exception as e:
            print(f"Error al actualizar la tabla de campañas: {str(e)}")
            return

        self.grand_total_tabla.delete(*self.grand_total_tabla.get_children())
        if all_subtotals:
            grand_total_delivered = 0
            grand_weighted_open = 0
            grand_weighted_click = 0
            grand_total_weight = 0
            grand_total_unique = 0
            grand_total_sum_value = 0
            grand_total_count = 0
            grand_total_per_recipient_weighted = 0
            grand_total_delivered_for_weight = 0

            for subtotal in all_subtotals:
                if subtotal:
                    grand_total_delivered += subtotal["delivered"]
                    grand_weighted_open += subtotal["weighted_open"]
                    grand_weighted_click += subtotal["weighted_click"]
                    grand_total_weight += subtotal["total_weight"]
                    grand_total_unique += subtotal["unique"]
                    grand_total_sum_value += subtotal["sum_value"]
                    grand_total_count += subtotal["count"]
                    grand_total_per_recipient_weighted += subtotal["per_recipient_weighted"]
                    grand_total_delivered_for_weight += subtotal["delivered_for_weight"]

            if grand_total_weight > 0:
                grand_avg_open_rate = round((grand_weighted_open / grand_total_weight) * 100, 2)
                grand_avg_click_rate = round((grand_weighted_click / grand_total_weight) * 100, 2)
                grand_per_recipient_weighted_avg = grand_total_per_recipient_weighted / grand_total_delivered_for_weight if grand_total_delivered_for_weight > 0 else 0.0
                values = [
                    "",
                    "Total General",
                    format_percentage(grand_avg_open_rate),
                    format_percentage(grand_avg_click_rate),
                    format_number(grand_total_delivered),
                    format_number(int(grand_total_unique)),
                    format_number(grand_total_sum_value, is_currency=True),
                    format_number(grand_per_recipient_weighted_avg, is_currency=True),
                    format_number(int(grand_total_count)),
                ]
                self.grand_total_tabla.insert("", "end", values=values, tags=("grand_total",))

    def analizar(self):
        input_str = self.entry.get().strip()
        if not input_str:
            # Si no hay entrada, mostramos un mensaje en un cuadro de diálogo
            messagebox.showinfo("Información", "Por favor, ingrese códigos de país, palabras clave o números de campaña.")
            return

        # Si no estamos en modo análisis, cambiamos a la vista de dos paneles
        if not self.is_analysis_mode:
            self.setup_analysis_view()

        # Verificar que self.resultados_tabla exista después de setup_analysis_view
        if not self.resultados_tabla:
            messagebox.showerror("Error", "No se pudo inicializar la tabla de resultados. Por favor, intenta de nuevo.")
            return

        self.resultados_tabla.delete(*self.resultados_tabla.get_children())
        self.resultados_tabla.insert("", "end", values=("", "", "Buscando información...", "", ""))
        
        self.entry.config(state=tk.DISABLED)
        self.btn_analizar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_exportar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_nuevo_rango.config(state=tk.DISABLED, bg="#A9A9A9")

        self.resultados_label.config(text=f"Resultados del análisis: {input_str}", font=("TkDefaultFont", 12, "bold"), fg="#23376D")
        self.email_preview.resultados_label = self.resultados_label  # Actualizar en EmailPreview

        self.root.update()
        
        seleccionados = seleccionar_campanas(self.campanas, input_str)
        if not seleccionados:
            self.resultados_tabla.delete(*self.resultados_tabla.get_children())
            self.resultados_tabla.insert("", "end", values=("", "", "No se seleccionaron campañas.", "", ""))
        else:
            self.last_results.clear()
            self.resultados_tabla.delete(*self.resultados_tabla.get_children())
            
            resultados_por_fecha_pais = defaultdict(lambda: defaultdict(list))
            for camp in seleccionados:
                idx, campaign_id, campaign_name, send_time, open_rate, click_rate, delivered, subject, preview, template_id, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
                try:
                    send_date = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                except ValueError as ve:
                    send_date = send_time
                partes = campaign_name.split("_")
                pais = partes[-1].strip().lower() if len(partes) > 1 else "desconocido"
                analysis_end_date = datetime.now().strftime("%Y-%m-%d")
                
                total_clicks = 0
                aggregated_data, error = query_metric_aggregates_post(campaign_id, send_date, analysis_end_date)
                if error:
                    resultados_por_fecha_pais[send_date][campaign_name].append((error, None, total_clicks))
                else:
                    totales = {}
                    if aggregated_data and "data" in aggregated_data:
                        attributes = aggregated_data["data"].get("attributes", {})
                        results = attributes.get("data", [])
                        for entry in results:
                            dims = entry.get("dimensions", [])
                            count = sum(entry.get("measurements", {}).get("count", [0]))
                            total_clicks += count
                            if dims:
                                url_clicked = dims[0]
                                unique = sum(entry.get("measurements", {}).get("unique", [0]))
                                totales[url_clicked] = {"count": count, "unique": unique}
                    if totales:
                        self.last_results[(campaign_name, send_date)] = totales
                        resultados_por_fecha_pais[send_date][campaign_name].append((None, totales, total_clicks))
                    else:
                        resultados_por_fecha_pais[send_date][campaign_name].append(("No se encontraron clics para esta campaña.", None, total_clicks))

            self.resultados_tabla.delete(*self.resultados_tabla.get_children())
            
            for fecha in sorted(resultados_por_fecha_pais.keys()):
                self.resultados_tabla.insert("", "end", values=("", "", f"Fecha de envío: {fecha}", "", ""), tags=("bold",))
                campañas_ordenadas = {}
                for campaign_name, resultados in resultados_por_fecha_pais[fecha].items():
                    total_clics = 0
                    for _, totales, total_clicks_campaign in resultados:
                        if totales:
                            total_clics += sum(data["count"] for data in totales.values())
                    campañas_ordenadas[campaign_name] = total_clics
                
                for campaign_name in sorted(campañas_ordenadas, key=lambda x: campañas_ordenadas[x], reverse=True):
                    resultados = resultados_por_fecha_pais[fecha][campaign_name]
                    for error, totales, total_clicks in resultados:
                        self.resultados_tabla.insert("", "end", values=(campaign_name, total_clicks, "", "", ""))
                        todas_las_urls = []
                        if error:
                            self.resultados_tabla.insert("", "end", values=("", "", error, "", ""))
                        else:
                            for url, data in totales.items():
                                todas_las_urls.append((url, data["count"], data["unique"]))
                        todas_las_urls.sort(key=lambda x: x[1], reverse=True)
                        for url, clics_totales, clics_unicos in todas_las_urls:
                            self.resultados_tabla.insert("", "end", values=("", "", url, clics_totales, clics_unicos))
                    self.resultados_tabla.insert("", "end", values=("", "", "", "", ""))
            self.resultados_tabla.insert("", "end", values=("", "", "Análisis completado.", "", ""))

        self.entry.config(state=tk.NORMAL)
        self.btn_analizar.config(state=tk.NORMAL, bg="#23376D")
        self.btn_exportar.config(state=tk.NORMAL, bg="#23376D")  # Habilitado porque siempre hay campañas
        self.btn_nuevo_rango.config(state=tk.NORMAL, bg="#23376D")

        self.entry.delete(0, tk.END)
        self.entry.focus_set()

    def nuevo_rango(self):
        if self.webview_window:
            self.webview_window.destroy()
            self.webview_window = None
            self.email_preview.webview_window[0] = None  # Actualizar en EmailPreview

        for after_id in list(self.root.after_ids):
            self.root.after_cancel(after_id)
        self.root.quit()
        self.root.destroy()
        main()

def abrir_resultados(list_start_date, list_end_date):
    root = tk.Tk()
    root.title(f"Resultados de Campañas ({list_start_date} a {list_end_date})")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    window_width = int(screen_width * 0.7)
    window_height = int(screen_height * 0.7)
    root.geometry(f"{window_width}x{window_height}")

    root.after_ids = []

    texto_resultados = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=35)
    texto_resultados.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    texto_resultados.insert(tk.END, "Cargando...\n")

    def update_text(message):
        texto_resultados.delete(1.0, tk.END)
        texto_resultados.insert(tk.END, f"{message}\n")
        root.update()

    root.update()

    campanas, error = obtener_campanas(list_start_date, list_end_date, update_text)
    if error:
        texto_resultados.delete(1.0, tk.END)
        texto_resultados.insert(tk.END, f"Error al cargar campañas: {error}\n")
        tk.Button(root, text="Cerrar", command=lambda: [root.quit(), root.destroy()], 
                 bg="#23376D", fg="white", activebackground="#3A4F9A", 
                 activeforeground="white", font=("TkDefaultFont", 10, "bold")).pack(pady=10)
    else:
        texto_resultados.pack_forget()
        app = ResultadosApp(root, campanas, list_start_date, list_end_date)

    root.mainloop()

def main():
    selector = DateSelector(abrir_resultados)
    fechas = selector.get_result()
    if not fechas:
        print("No se seleccionó ninguna fecha.")

if __name__ == "__main__":
    import locale
    from datetime import datetime
    main()