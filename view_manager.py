import tkinter as tk
from tkinter import ttk
import tkinter.messagebox

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
        self.filter_var = tk.StringVar(value="Todos")
        self.resultados_tabla = None
        
        # NUEVAS VARIABLES PARA EL SISTEMA DROPDOWN
        self.expanded_rows = {}  # Almacena el estado de expansión de cada fila
        self.audience_data = {}  # Almacena los datos completos de audiencias
        self.audience_names_cache = {}  # AGREGAR CACHE DE NOMBRES

    def create_campanas_tabla(self, treeview_frame, total_table_width):
        # Crear la tabla CON la nueva columna "OpenUnique"
        self.campanas_tabla = ttk.Treeview(treeview_frame, columns=(
            "Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OrderUnique",
            "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "OpenUnique", "Subject", "Preview"
        ), show="headings")
        self.campanas_tabla.grid(row=0, column=0, sticky="nsew")

        # Configurar scrollbar vertical
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.campanas_tabla.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.campanas_tabla.configure(yscrollcommand=scrollbar.set)

        # Configurar estilos
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        # CAMBIAR EL TÍTULO DE LA PRIMERA COLUMNA PARA INDICAR FUNCIONALIDAD
        self.campanas_tabla.heading("Numero", text="# / Audiencias")
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
        self.campanas_tabla.heading("OpenUnique", text="Open Únicos")  # NUEVA COLUMNA
        self.campanas_tabla.heading("Subject", text="Subject Line")
        self.campanas_tabla.heading("Preview", text="Preview Text")

        # Configurar anchos de columnas (CON la nueva columna OpenUnique)
        column_widths = {
            "Numero": int(total_table_width * 0.05),       # Reducido para dar espacio
            "Nombre": int(total_table_width * 0.08),       # Reducido para dar espacio
            "FechaEnvio": int(total_table_width * 0.06),   
            "OpenRate": int(total_table_width * 0.05),     
            "ClickRate": int(total_table_width * 0.05),    
            "Recibios": int(total_table_width * 0.06),     
            "OrderUnique": int(total_table_width * 0.05),  
            "OrderSumValue": int(total_table_width * 0.07), # Reducido para dar espacio
            "OrderSumValueLocal": int(total_table_width * 0.07), # Reducido para dar espacio
            "PerRecipient": int(total_table_width * 0.07), # Reducido para dar espacio
            "OrderCount": int(total_table_width * 0.05),   
            "OpenUnique": int(total_table_width * 0.05),   # NUEVA COLUMNA
            "Subject": int(total_table_width * 0.13),      # Reducido para dar espacio a OpenUnique
            "Preview": int(total_table_width * 0.13),      # Reducido para dar espacio a OpenUnique
        }

        self.column_widths = column_widths

        # Aplicar configuraciones de columnas
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
        self.campanas_tabla.column("OpenUnique", width=column_widths["OpenUnique"], anchor="center")  # NUEVA COLUMNA
        self.campanas_tabla.column("Subject", width=column_widths["Subject"])
        self.campanas_tabla.column("Preview", width=column_widths["Preview"])

        # Configurar estilos para las filas de audiencias
        self.campanas_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")
        self.campanas_tabla.tag_configure("campaign_row", font=("Arial", 10))
        self.campanas_tabla.tag_configure("audience_detail", font=("Arial", 9), background="#F5F5F5")
        self.campanas_tabla.tag_configure("audience_header", font=("Arial", 9, "bold"), background="#E6F3FF")

        # NUEVOS BINDINGS PARA MANEJAR CLICS
        self.campanas_tabla.bind("<Button-1>", self.on_single_click)  # Clic simple
        self.campanas_tabla.bind("<Double-1>", self.on_double_click)  # Doble clic
        self.campanas_tabla.bind("<Button-3>", self.show_context_menu)  # Clic derechoimport tkinter as tk
from tkinter import ttk
import tkinter.messagebox

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
        self.filter_var = tk.StringVar(value="Todos")
        self.resultados_tabla = None
        
        # NUEVAS VARIABLES PARA EL SISTEMA DROPDOWN
        self.expanded_rows = {}  # Almacena el estado de expansión de cada fila
        self.audience_data = {}  # Almacena los datos completos de audiencias
        self.audience_names_cache = {}  # AGREGAR CACHE DE NOMBRES

    def create_campanas_tabla(self, treeview_frame, total_table_width):
        # Crear la tabla CON la nueva columna "OpenUnique"
        self.campanas_tabla = ttk.Treeview(treeview_frame, columns=(
            "Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OrderUnique",
            "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "OpenUnique", "Subject", "Preview"
        ), show="headings")
        self.campanas_tabla.grid(row=0, column=0, sticky="nsew")

        # Configurar scrollbar vertical
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.campanas_tabla.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.campanas_tabla.configure(yscrollcommand=scrollbar.set)

        # Configurar estilos
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        # CAMBIAR EL TÍTULO DE LA PRIMERA COLUMNA PARA INDICAR FUNCIONALIDAD
        self.campanas_tabla.heading("Numero", text="# / Audiencias")
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
        self.campanas_tabla.heading("OpenUnique", text="Open Únicos")  # NUEVA COLUMNA
        self.campanas_tabla.heading("Subject", text="Subject Line")
        self.campanas_tabla.heading("Preview", text="Preview Text")

        # Configurar anchos de columnas (CON la nueva columna OpenUnique)
        column_widths = {
            "Numero": int(total_table_width * 0.05),       # Reducido para dar espacio
            "Nombre": int(total_table_width * 0.08),       # Reducido para dar espacio
            "FechaEnvio": int(total_table_width * 0.06),   
            "OpenRate": int(total_table_width * 0.05),     
            "ClickRate": int(total_table_width * 0.05),    
            "Recibios": int(total_table_width * 0.06),     
            "OrderUnique": int(total_table_width * 0.05),  
            "OrderSumValue": int(total_table_width * 0.07), # Reducido para dar espacio
            "OrderSumValueLocal": int(total_table_width * 0.07), # Reducido para dar espacio
            "PerRecipient": int(total_table_width * 0.07), # Reducido para dar espacio
            "OrderCount": int(total_table_width * 0.05),   
            "OpenUnique": int(total_table_width * 0.05),   # NUEVA COLUMNA
            "Subject": int(total_table_width * 0.13),      # Reducido para dar espacio a OpenUnique
            "Preview": int(total_table_width * 0.13),      # Reducido para dar espacio a OpenUnique
        }

        self.column_widths = column_widths

        # Aplicar configuraciones de columnas
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
        self.campanas_tabla.column("OpenUnique", width=column_widths["OpenUnique"], anchor="center")  # NUEVA COLUMNA
        self.campanas_tabla.column("Subject", width=column_widths["Subject"])
        self.campanas_tabla.column("Preview", width=column_widths["Preview"])

        # Configurar estilos para las filas de audiencias
        self.campanas_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")
        self.campanas_tabla.tag_configure("campaign_row", font=("Arial", 10))
        self.campanas_tabla.tag_configure("audience_detail", font=("Arial", 9), background="#F5F5F5")
        self.campanas_tabla.tag_configure("audience_header", font=("Arial", 9, "bold"), background="#E6F3FF")

        # NUEVOS BINDINGS PARA MANEJAR CLICS
        self.campanas_tabla.bind("<Button-1>", self.on_single_click)  # Clic simple
        self.campanas_tabla.bind("<Double-1>", self.on_double_click)  # Doble clic
        self.campanas_tabla.bind("<Button-3>", self.show_context_menu)  # Clic derecho

    # NUEVOS MÉTODOS PARA MANEJAR LA EXPANSIÓN/CONTRACCIÓN
    def on_single_click(self, event):
        """Maneja el clic simple para expandir/contraer audiencias solo en la primera columna."""
        # Identificar qué columna fue clickeada
        column = self.campanas_tabla.identify_column(event.x)
        item = self.campanas_tabla.identify_row(event.y)
        
        if not item:
            return
            
        values = self.campanas_tabla.item(item, "values")
        tags = self.campanas_tabla.item(item, "tags")
        
        if column == "#1":  # Solo en la primera columna (Numero)
            # Verificar si es una fila de campaña (no de grupo o subtotal)
            if any(tag.startswith("campaign_") for tag in tags):
                self.toggle_audience_details(item)
                
        # NUEVO: Verificar si es una fila de audiencia con icono de carga EN CUALQUIER COLUMNA
        if "audience_detail" in tags:
            audience_text = values[1] if len(values) > 1 else ""
            if "🔃" in audience_text:
                self.load_audience_size(item, audience_text)

    def on_double_click(self, event):
        """Maneja el doble clic para preview del template (funcionalidad original)."""
        # Solo activar preview si NO es en la primera columna
        column = self.campanas_tabla.identify_column(event.x)
        if column != "#1":
            self.email_preview.preview_template(event)

    def toggle_audience_details(self, item_id):
        """Alterna entre expandir y contraer los detalles de audiencias."""
        if item_id in self.expanded_rows and self.expanded_rows[item_id]:
            self.contract_audience_details(item_id)
        else:
            self.expand_audience_details(item_id)

    def expand_audience_details(self, item_id):
        """Expande los detalles de audiencias para una campaña específica."""
        if item_id not in self.audience_data:
            return

        campaign_data = self.audience_data[item_id]
        if not campaign_data or campaign_data == "N/A":
            return

        # Marcar como expandido
        self.expanded_rows[item_id] = True
        
        # Actualizar el indicador en la primera columna
        self.update_row_indicator(item_id, expanded=True)

        # Obtener la posición donde insertar los detalles
        item_index = self.campanas_tabla.index(item_id)
        current_pos = item_index + 1
        
        # Insertar filas de detalles de audiencias
        if 'included' in campaign_data and campaign_data['included']:
            # Insertar encabezado de audiencias incluidas
            header_id = self.campanas_tabla.insert("", current_pos, 
                values=("", "📋 Audiencias Incluidas", "", "", "", "", "", "", "", "", "", "", ""),
                tags=("audience_header",))
            current_pos += 1
            
            # Insertar cada audiencia incluida
            for i, audience_info in enumerate(campaign_data['included']):
                if isinstance(audience_info, dict):
                    # Ya tiene información de tamaño cargada
                    audience_text = audience_info['display_text']
                else:
                    # Solo tiene el nombre, añadir botón para cargar tamaño - CAMBIO AQUÍ
                    audience_text = f"  • {audience_info}  🔃"
                
                detail_id = self.campanas_tabla.insert("", current_pos,
                    values=("", audience_text, "", "", "", "", "", "", "", "", "", "", ""),
                    tags=("audience_detail",))
                current_pos += 1

        if 'excluded' in campaign_data and campaign_data['excluded']:
            # Insertar encabezado de audiencias excluidas
            header_id = self.campanas_tabla.insert("", current_pos,
                values=("", "🚫 Audiencias Excluidas", "", "", "", "", "", "", "", "", "", "", ""),
                tags=("audience_header",))
            current_pos += 1
            
            # Insertar cada audiencia excluida
            for i, audience_info in enumerate(campaign_data['excluded']):
                if isinstance(audience_info, dict):
                    # Ya tiene información de tamaño cargada
                    audience_text = audience_info['display_text']
                else:
                    # Solo tiene el nombre, añadir botón para cargar tamaño - CAMBIO AQUÍ
                    audience_text = f"  • {audience_info}  🔃"
                
                detail_id = self.campanas_tabla.insert("", current_pos,
                    values=("", audience_text, "", "", "", "", "", "", "", "", "", "", ""),
                    tags=("audience_detail",))
                current_pos += 1

    def load_audience_size(self, item_id, audience_text):
        """Carga el tamaño de una audiencia específica."""
        import threading
        import requests
        from config import KLAVIYO_URLS, HEADERS_KLAVIYO
        
        # Extraer el nombre de la audiencia (quitar símbolos y botón)
        audience_name = audience_text.replace("  • ", "").replace("  🔃", "").strip()
        
        # Mostrar indicador de carga
        loading_text = audience_text.replace("🔃", "⏳")
        self.campanas_tabla.item(item_id, values=("", loading_text, "", "", "", "", "", "", "", "", "", "", ""))
        
        def fetch_size():
            """Función para obtener el tamaño en un hilo separado."""
            try:
                # Buscar el audience_id en el cache de nombres
                audience_id = None
                for aid, name in self.audience_names_cache.items():
                    if name == audience_name:
                        audience_id = aid
                        break
                
                if not audience_id:
                    # No se encontró el ID, mostrar sin tamaño
                    final_text = audience_text.replace("  🔃", " (ID no encontrado)")
                    self.campanas_tabla.after(0, lambda: self.campanas_tabla.item(
                        item_id, values=("", final_text, "", "", "", "", "", "", "", "", "", "", "")
                    ))
                    return
                
                # Intentar obtener como lista primero
                profile_count = None
                url = f"{KLAVIYO_URLS['LISTS']}{audience_id}/?additional-fields[list]=profile_count"
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    profile_count = data['data']['attributes'].get('profile_count', 0)
                else:
                    # Intentar como segmento
                    url = f"{KLAVIYO_URLS['SEGMENTS']}{audience_id}/?additional-fields[segment]=profile_count"
                    response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        profile_count = data['data']['attributes'].get('profile_count', 0)
                
                # Actualizar la interfaz en el hilo principal
                if profile_count is not None:
                    # Quitar el icono de carga y añadir el conteo
                    final_text = audience_text.replace("  🔃", f" ({profile_count:,})")
                else:
                    final_text = audience_text.replace("  🔃", " (No disponible)")
                
                # Programar la actualización en el hilo principal
                self.campanas_tabla.after(0, lambda: self.campanas_tabla.item(
                    item_id, values=("", final_text, "", "", "", "", "", "", "", "", "", "", "")
                ))
                
            except Exception as e:
                # En caso de error, quitar el botón
                final_text = audience_text.replace("  🔃", f" (Error: {str(e)})")
                self.campanas_tabla.after(0, lambda: self.campanas_tabla.item(
                    item_id, values=("", final_text, "", "", "", "", "", "", "", "", "", "", "")
                ))
        
        # Ejecutar en un hilo separado para no bloquear la UI
        thread = threading.Thread(target=fetch_size)
        thread.daemon = True
        thread.start()            

    def contract_audience_details(self, item_id):
        """Contrae los detalles de audiencias para una campaña específica."""
        # Marcar como contraído
        self.expanded_rows[item_id] = False
        
        # Actualizar el indicador en la primera columna
        self.update_row_indicator(item_id, expanded=False)

        # Encontrar y eliminar todas las filas de detalles de audiencias
        items_to_remove = []
        item_index = self.campanas_tabla.index(item_id)
        
        # Buscar las filas siguientes que sean de audiencias
        for child_id in self.campanas_tabla.get_children():
            child_index = self.campanas_tabla.index(child_id)
            if child_index > item_index:
                tags = self.campanas_tabla.item(child_id, "tags")
                if "audience_detail" in tags or "audience_header" in tags:
                    items_to_remove.append(child_id)
                else:
                    # Si encontramos una fila que no es de audiencias, parar
                    break

        # Eliminar las filas encontradas
        for item in items_to_remove:
            self.campanas_tabla.delete(item)

    def update_row_indicator(self, item_id, expanded=False):
        """Actualiza el indicador ▶/▼ en la primera columna."""
        current_values = list(self.campanas_tabla.item(item_id, "values"))
        
        # Extraer el número de campaña del valor actual
        current_first_col = str(current_values[0])
        if current_first_col.startswith("▶ ") or current_first_col.startswith("▼ "):
            campaign_number = current_first_col[2:]
        else:
            campaign_number = current_first_col
        
        # Actualizar el indicador
        if expanded:
            current_values[0] = f"▼ {campaign_number}"
        else:
            current_values[0] = f"▶ {campaign_number}"
        
        # Actualizar la fila
        self.campanas_tabla.item(item_id, values=current_values)

    def store_audience_data(self, item_id, audience_info):
        """Almacena los datos completos de audiencias para una campaña."""
        # Primero intentar obtener datos completos desde el cache temporal
        tags = self.campanas_tabla.item(item_id, "tags")
        campaign_id = None
        
        for tag in tags:
            if tag.startswith("campaign_"):
                campaign_id = tag.replace("campaign_", "")
                break
        
        if campaign_id:
            # Buscar en datos temporales usando el campaign_id
            temp_key = f"temp_{campaign_id}"
            if temp_key in self.audience_data:
                # Usar datos completos del cache temporal
                self.audience_data[item_id] = self.audience_data[temp_key]
                # Limpiar el cache temporal
                del self.audience_data[temp_key]
                return
        
        # Si no hay datos temporales, parsear la información de audiencias
        if audience_info == "N/A" or not audience_info:
            self.audience_data[item_id] = None
            return

        parsed_data = self.parse_audience_info(audience_info)
        self.audience_data[item_id] = parsed_data

    def parse_audience_info(self, audience_info):
        """Parsea la información de audiencias para extraer los nombres completos."""
        if not audience_info or audience_info == "N/A":
            return None
        
        try:
            # El formato viene como: "Inc: Nombre1, Nombre2, +3; Exc: Nombre4, Nombre5"
            result = {}
            
            # Dividir por "; " para separar incluidas y excluidas
            parts = audience_info.split("; ")
            
            for part in parts:
                if part.startswith("Inc: "):
                    # Extraer audiencias incluidas
                    included_str = part[5:]  # Quitar "Inc: "
                    included_list = [name.strip() for name in included_str.split(", ")]
                    # Filtrar los indicadores "+X" 
                    included_list = [name for name in included_list if not name.startswith("+")]
                    result['included'] = included_list
                    
                elif part.startswith("Exc: "):
                    # Extraer audiencias excluidas
                    excluded_str = part[5:]  # Quitar "Exc: "
                    excluded_list = [name.strip() for name in excluded_str.split(", ")]
                    # Filtrar los indicadores "+X"
                    excluded_list = [name for name in excluded_list if not name.startswith("+")]
                    result['excluded'] = excluded_list
            
            return result if result else None
            
        except Exception as e:
            print(f"Error parseando audiencias: {e}")
            return None

    # MÉTODO PARA PASAR EL CACHE DE NOMBRES DESDE CAMPAIGN_LOGIC
    def set_audience_names_cache(self, cache):
        """Establece el cache de nombres de audiencias."""
        self.audience_names_cache = cache

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
            tags = self.campanas_tabla.item(selected_item[0], "tags")
            if tags and len(tags) > 0:
                campaign_id = tags[0] if tags[0].startswith("campaign_") else None
                if campaign_id:
                    campaign_id = campaign_id.replace("campaign_", "")

            if not campaign_id:
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
        """Crea y configura la tabla de total general."""
        self.grand_total_tabla = ttk.Treeview(parent_frame, columns=(
            "Numero", "Nombre", "OpenRate", "ClickRate", "Recibios", "OrderUnique",
            "OrderSumValue", "PerRecipient", "OrderCount", "OpenUnique"
        ), show="headings", height=1)
        
        self.grand_total_tabla.grid(row=3, column=0, sticky="ew", pady=5)
        parent_frame.columnconfigure(0, weight=1)  # Importante para expansión
        
        # Configurar encabezados
        self.grand_total_tabla.heading("Numero", text="")
        self.grand_total_tabla.heading("Nombre", text="")
        self.grand_total_tabla.heading("OpenRate", text="Open Rate")
        self.grand_total_tabla.heading("ClickRate", text="Click Rate")
        self.grand_total_tabla.heading("Recibios", text="Recibidos")
        self.grand_total_tabla.heading("OrderUnique", text="Unique Orders")
        self.grand_total_tabla.heading("OrderSumValue", text="Total Value (USD)")
        self.grand_total_tabla.heading("PerRecipient", text="Per Recipient")
        self.grand_total_tabla.heading("OrderCount", text="Order Count")
        self.grand_total_tabla.heading("OpenUnique", text="Open Únicos")
        
        # Configurar anchos con valores por defecto seguros
        self.grand_total_tabla.column("Numero", width=0, stretch=False)
        self.grand_total_tabla.column("Nombre", width=column_widths.get("Nombre", 150), stretch=True)
        self.grand_total_tabla.column("OpenRate", width=column_widths.get("OpenRate", 80), stretch=True)
        self.grand_total_tabla.column("ClickRate", width=column_widths.get("ClickRate", 80), stretch=True)
        self.grand_total_tabla.column("Recibios", width=column_widths.get("Recibios", 100), stretch=True)
        self.grand_total_tabla.column("OrderUnique", width=column_widths.get("OrderUnique", 100), stretch=True)
        self.grand_total_tabla.column("OrderSumValue", width=column_widths.get("OrderSumValue", 120), stretch=True)
        self.grand_total_tabla.column("PerRecipient", width=column_widths.get("PerRecipient", 100), stretch=True)
        self.grand_total_tabla.column("OrderCount", width=column_widths.get("OrderCount", 100), stretch=True)
        self.grand_total_tabla.column("OpenUnique", width=column_widths.get("OpensUnicos", 100), stretch=True)
        
        self.grand_total_tabla.tag_configure("grand_total", font=("Arial", 11, "bold"), 
                                            background="#23376D", foreground="white")

    def setup_metrics_view(self, entry_frame, buttons_frame, grouping_var, show_local_value, update_grouping_callback, start_date, end_date):
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
       
        # Label con el rango de fechas
        range_label = tk.Label(self.left_frame, text=f"Campañas en el rango seleccionado: {start_date} a {end_date}", 
                              fg="#23376D", font=("TkDefaultFont", 12, "bold"))
        range_label.grid(row=1, column=0, sticky="ew", pady=5)

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

    def update_resultados_tabla_columns(self):
        """Actualiza las columnas de resultados_tabla según el filtro seleccionado."""
        filter_type = self.filter_var.get()
        
        # Definir las columnas base
        columns = ("Campaign", "Clics Totales", "URL", "Clics Totales URL", "Clics Únicos")
        headings = {"Campaign": "Campaña", "Clics Totales": "Clics Totales", "URL": "URL", 
                   "Clics Totales URL": "Clics Totales URL", "Clics Únicos": "Clics Únicos"}

        # Añadir columna dinámica según el filtro
        if filter_type == "Producto":
            columns = ("Campaign", "Clics Totales", "URL", "Clics Totales URL", "Clics Únicos", "SKU")
            headings["SKU"] = "SKU"
        elif filter_type == "Categoría":
            columns = ("Campaign", "Clics Totales", "URL", "Clics Totales URL", "Clics Únicos", "ID Categoria")
            headings["ID Categoria"] = "ID Categoría"

        # Actualizar las columnas de la tabla
        self.resultados_tabla.configure(columns=columns)
        
        # Configurar los encabezados
        for col in columns:
            self.resultados_tabla.heading(col, text=headings.get(col, col))

        # Configurar anchos de columnas
        total_resultados_width = int(self.screen_width * 0.5)
        self.resultados_tabla.column("Campaign", width=int(total_resultados_width * 0.10), anchor="w")  # Reducido de 0.15 a 0.10
        self.resultados_tabla.column("Clics Totales", width=int(total_resultados_width * 0.10), anchor="center")  # Reducido de 0.15 a 0.10
        self.resultados_tabla.column("URL", width=int(total_resultados_width * 0.35), anchor="w")  # Reducido de 0.40 a 0.35
        self.resultados_tabla.column("Clics Totales URL", width=int(total_resultados_width * 0.15), anchor="center")
        self.resultados_tabla.column("Clics Únicos", width=int(total_resultados_width * 0.15), anchor="center")
        
        # Configurar la columna dinámica (si existe)
        if filter_type in ["Producto", "Categoría"]:
            dynamic_col = "SKU" if filter_type == "Producto" else "ID Categoria"
            self.resultados_tabla.column(dynamic_col, width=int(total_resultados_width * 0.15), anchor="center")

    def on_resultados_double_click(self, event):
        """Maneja el evento de doble clic en resultados_tabla para abrir el visualizador con la URL seleccionada."""
        try:
            # Identificar la fila seleccionada
            selected_item = self.resultados_tabla.selection()
            if not selected_item:
                return

            # Obtener los valores de la fila
            values = self.resultados_tabla.item(selected_item[0], "values")
            url = values[2]  # La URL está en la tercera columna (índice 2)

            # Verificar si la fila contiene una URL válida (no una fila de fecha, campaña o mensaje)
            if not url or url.startswith("Fecha de envío:") or url.startswith("No se encontraron") or url == "Análisis completado.":
                return

            # Llamar al método del visualizador para mostrar la URL
            self.email_preview.preview_url(url)

        except Exception as e:
            print(f"Error al abrir el visualizador: {str(e)}")

    def copy_url(self, event=None):
        """Copia la URL seleccionada al portapapeles cuando se presiona Ctrl+C."""
        selected_item = self.resultados_tabla.selection()
        if not selected_item:
            return

        item = self.resultados_tabla.item(selected_item[0])
        values = item["values"]
        url = values[2]  # La URL está en la tercera columna (índice 2)

        # Solo copiar si la fila contiene una URL válida
        if url and not url.startswith("Fecha de envío:") and not url.startswith("No se encontraron") and not url == "Análisis completado.":
            self.resultados_tabla.clipboard_clear()
            self.resultados_tabla.clipboard_append(url)

    def copy_url_context(self):
        """Copia la URL seleccionada al portapapeles desde el menú contextual."""
        selected_item = self.resultados_tabla.selection()
        if not selected_item:
            return

        item = self.resultados_tabla.item(selected_item[0])
        values = item["values"]
        url = values[2]  # La URL está en la tercera columna (índice 2)

        # Solo copiar si la fila contiene una URL válida
        if url and not url.startswith("Fecha de envío:") and not url.startswith("No se encontraron") and not url == "Análisis completado.":
            self.resultados_tabla.clipboard_clear()
            self.resultados_tabla.clipboard_append(url)

    def show_context_menu_results(self, event):
        """Muestra el menú contextual al hacer clic derecho en resultados_tabla."""
        # Seleccionar la fila bajo el cursor si no está seleccionada
        item = self.resultados_tabla.identify_row(event.y)
        if item:
            self.resultados_tabla.selection_set(item)
            # Verificar si la fila contiene una URL válida
            values = self.resultados_tabla.item(item, "values")
            url = values[2]  # La URL está en la tercera columna (índice 2)
            if url and not url.startswith("Fecha de envío:") and not url.startswith("No se encontraron") and not url == "Análisis completado.":
                self.resultados_context_menu.post(event.x_root, event.y_root)

    def setup_analysis_view(self, grouping_var, show_local_value, update_grouping_callback, cerrar_analisis_callback, filter_callback=None, start_date=None, end_date=None):
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

        # Label con el rango de fechas
        range_label = tk.Label(self.left_frame, text=f"Campañas en el rango seleccionado: {start_date or ''} a {end_date or ''}", 
                              fg="#23376D", font=("TkDefaultFont", 12, "bold"))
        range_label.grid(row=1, column=0, sticky="ew", pady=5)

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

        # Frame para el título, el filtro y el botón de cerrar
        self.results_header_frame = tk.Frame(self.right_frame)
        self.results_header_frame.grid(row=0, column=0, sticky="ew", pady=5)

        self.resultados_label = tk.Label(self.results_header_frame, text="Resultados del análisis:", font=("TkDefaultFont", 12, "bold"), fg="#23376D")
        self.resultados_label.pack(side=tk.LEFT, padx=5)
        self.email_preview.resultados_label = self.resultados_label

        # Añadir el Combobox para el filtro
        tk.Label(self.results_header_frame, text="Filtrar por:", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)
        filter_options = ttk.Combobox(self.results_header_frame, textvariable=self.filter_var, values=["Todos", "Producto", "Categoría"], state="readonly")
        filter_options.pack(side=tk.LEFT, padx=5)
        if filter_callback:
            # Actualizar las columnas cuando cambie el filtro
            def combined_callback(event):
                self.update_resultados_tabla_columns()
                filter_callback()
            filter_options.bind("<<ComboboxSelected>>", combined_callback)

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

        # Crear la tabla con columnas base (se actualizarán dinámicamente)
        self.resultados_tabla = ttk.Treeview(content_frame, columns=("Campaign", "Clics Totales", "URL", "Clics Totales URL", "Clics Únicos"), show="headings")
        self.resultados_tabla.grid(row=0, column=0, sticky="nsew")
        self.email_preview.resultados_tabla = self.resultados_tabla
        self.exporter.resultados_tabla = self.resultados_tabla

        # Añadir scrollbar vertical para resultados
        resultados_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.resultados_tabla.yview)
        resultados_scrollbar.grid(row=0, column=1, sticky="ns")
        self.resultados_tabla.configure(yscrollcommand=resultados_scrollbar.set)

        # Configurar encabezados y anchos iniciales
        self.update_resultados_tabla_columns()

        # Añadir binding para el evento de doble clic
        self.resultados_tabla.bind("<Double-1>", self.on_resultados_double_click)

        # Añadir bindings para copiar URL
        self.resultados_tabla.bind("<Control-c>", self.copy_url)

        # Crear menú contextual para resultados_tabla
        self.resultados_context_menu = tk.Menu(self.resultados_tabla, tearoff=0)
        self.resultados_context_menu.add_command(label="Copiar enlace", command=self.copy_url_context)
        self.resultados_tabla.bind("<Button-3>", self.show_context_menu_results)

        self.resultados_tabla.tag_configure("bold", font=("Arial", 11, "bold"), foreground="#23376D")