import tkinter as tk
from tkinter import ttk

class ViewManager:
    def __init__(self, main_frame, screen_width, screen_height, email_preview, exporter):
        self.main_frame = main_frame
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.email_preview = email_preview
        self.exporter = exporter
        self.campanas_tabla = None
        self.grand_total_tabla = None
        self.column_widths = None
        self.left_frame = None

    def create_campanas_tabla(self, treeview_frame, total_table_width):
        """Crea y configura la tabla de campañas (campanas_tabla)."""
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

        # Configurar anchos de columnas
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

        self.column_widths = column_widths

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

        # Configurar el binding para el clic derecho en la tabla
        self.campanas_tabla.bind("<Button-3>", self.show_context_menu)

        # Actualizar referencias
        self.email_preview.campanas_tabla = self.campanas_tabla
        self.exporter.campanas_tabla = self.campanas_tabla

    def show_context_menu(self, event):
        """Muestra el menú contextual si el clic derecho ocurre en la columna 'Order Count'."""
        try:
            # Identificar la fila y columna donde se hizo clic derecho
            row_id = self.campanas_tabla.identify_row(event.y)
            column_id = self.campanas_tabla.identify_column(event.x)

            if not row_id or not column_id:
                return

            # Seleccionar la fila para que sea evidente qué campaña se está interactuando
            self.campanas_tabla.selection_set(row_id)

            # Verificar si el clic derecho ocurrió en la columna "Order Count"
            if column_id != "#11":  # "Order Count" es la columna 11
                return

            # Obtener los datos de la fila seleccionada
            selected_item = self.campanas_tabla.selection()
            if not selected_item:
                return

            values = self.campanas_tabla.item(selected_item[0], "values")
            campaign_name = values[1]  # Nombre de la campaña

            # Intentar obtener el campaign_id (puede estar en los tags o datos asociados)
            campaign_id = None
            # Los tags suelen usarse para almacenar identificadores como campaign_id
            tags = self.campanas_tabla.item(selected_item[0], "tags")
            if tags and len(tags) > 0:
                # Suponemos que el campaign_id podría estar en los tags
                # Esto depende de cómo campaign_logic.py llena la tabla
                campaign_id = tags[0] if tags[0].startswith("campaign_") else None
                if campaign_id:
                    campaign_id = campaign_id.replace("campaign_", "")

            if not campaign_id:
                # Si no está en los tags, mostramos un valor placeholder
                campaign_id = "No disponible"

            # Crear el menú contextual dinámicamente
            self.context_menu = tk.Menu(self.campanas_tabla, tearoff=0)
            self.context_menu.add_command(label=f"Campaña: {campaign_name}", state="disabled")
            self.context_menu.add_command(label=f"Campaign ID: {campaign_id}", state="disabled")
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Ver Perfiles que Realizaron Órdenes", 
                                        command=lambda: self.view_order_profiles_placeholder(campaign_name, campaign_id))

            # Mostrar el menú contextual en la posición del clic
            self.context_menu.post(event.x_root, event.y_root)

        except Exception as e:
            print(f"Error al mostrar el menú contextual: {str(e)}")

    def view_order_profiles_placeholder(self, campaign_name, campaign_id):
        """Método temporal para probar el menú contextual."""
        try:
            print(f"Visualizando perfiles para la campaña: {campaign_name} (ID: {campaign_id})")
            tk.messagebox.showinfo("Información", f"Visualizando perfiles para la campaña: {campaign_name}\nCampaign ID: {campaign_id}")
        except Exception as e:
            print(f"Error al visualizar perfiles: {str(e)}")

    def create_grand_total_tabla(self, parent_frame, column_widths):
        """Crea y configura la tabla de total general (grand_total_tabla)."""
        self.grand_total_tabla = ttk.Treeview(parent_frame, columns=(
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

    def setup_metrics_view(self, entry_frame, buttons_frame, grouping_var, show_local_value, update_grouping_callback):
        """Configura la vista inicial con solo la tabla de métricas."""
        # Limpiar el frame principal, pero preservar el campo de entrada y los botones
        for widget in self.main_frame.winfo_children():
            if widget not in (entry_frame, buttons_frame):
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
        grouping_options = ttk.Combobox(control_frame, textvariable=grouping_var, values=["País", "Fecha"], state="readonly")
        grouping_options.pack(side=tk.LEFT, padx=5)
        grouping_options.bind("<<ComboboxSelected>>", update_grouping_callback)

        tk.Checkbutton(control_frame, text="Mostrar Total Value (Local)", variable=show_local_value,
                       command=update_grouping_callback, fg="#23376D").pack(side=tk.LEFT, padx=5)
       
        tk.Label(self.left_frame, text="Campañas en el rango seleccionado:", fg="#23376D", font=("TkDefaultFont", 12, "bold")).grid(row=1, column=0, sticky="ew", pady=5)

        # Frame para el Treeview con scrollbar
        treeview_frame = tk.Frame(self.left_frame)
        treeview_frame.grid(row=2, column=0, sticky="nsew")
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        # Crear campanas_tabla con un ancho basado en el 90% de la pantalla
        total_table_width = int(self.screen_width * 0.9)
        self.create_campanas_tabla(treeview_frame, total_table_width)

        # Crear grand_total_tabla
        self.create_grand_total_tabla(self.left_frame, self.column_widths)

        # Actualizar grouping_var en Exporter
        self.exporter.grouping_var = grouping_var

    def setup_analysis_view(self, grouping_var, show_local_value, update_grouping_callback, cerrar_analisis_callback):
        """Configura la vista con dos paneles: métricas a la izquierda y resultados a la derecha."""
        self.email_preview.is_analysis_mode = True
        self.exporter.is_analysis_mode = True

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
        grouping_options = ttk.Combobox(control_frame, textvariable=grouping_var, values=["País", "Fecha"], state="readonly")
        grouping_options.pack(side=tk.LEFT, padx=5)
        grouping_options.bind("<<ComboboxSelected>>", update_grouping_callback)

        tk.Checkbutton(control_frame, text="Mostrar Total Value (Local)", variable=show_local_value,
                       command=update_grouping_callback, fg="#23376D").pack(side=tk.LEFT, padx=5)

        tk.Label(self.left_frame, text="Campañas en el rango seleccionado:", fg="#23376D", font=("TkDefaultFont", 12, "bold")).grid(row=1, column=0, sticky="ew", pady=5)

        # Frame para el Treeview con scrollbar
        treeview_frame = tk.Frame(self.left_frame)
        treeview_frame.grid(row=2, column=0, sticky="nsew")
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        # Crear campanas_tabla con un ancho ajustado (50% de la pantalla)
        total_table_width = int(self.screen_width * 0.5)
        self.create_campanas_tabla(treeview_frame, total_table_width)

        # Crear grand_total_tabla
        self.create_grand_total_tabla(self.left_frame, self.column_widths)

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
        self.email_preview.resultados_label = self.resultados_label

        # Botón para cerrar el panel de análisis
        self.btn_cerrar_analisis = tk.Button(self.results_header_frame, text="Cerrar Análisis", command=cerrar_analisis_callback,
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
        self.email_preview.resultados_tabla = self.resultados_tabla
        self.exporter.resultados_tabla = self.resultados_tabla

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