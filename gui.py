import tkinter as tk
from tkinter import ttk, scrolledtext
import ctypes  # Para manejar el escalado de DPI en Windows
import os  # Para verificar el sistema operativo

# Importar los componentes modulares
from date_selector import DateSelector
from email_preview import EmailPreview
from exporter import Exporter
from view_manager import ViewManager
from analyzer import Analyzer

# Importar tus funciones reales
from campaign_logic import obtener_campanas, mostrar_campanas_en_tabla
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
        self.show_local_value = tk.BooleanVar(value=False)
        self.webview_window = None
        self.is_analysis_mode = tk.BooleanVar(value=False)  # Controla si estamos mostrando el panel de resultados
        self.analyze_all_campaigns = tk.BooleanVar(value=True)  # Checkbox marcado por defecto
        self.template_ids = {}  # Diccionario para almacenar los template_id
        self.resultados_tabla = None  # Inicializar como None
        self.resultados_label = None  # Inicializar como None
        self.campanas_tabla = None  # Inicializar como None

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
            self.campanas_tabla,  # Se asignará después de inicializar
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
            self.campanas_tabla,  # Se asignará después de inicializar
            tk.StringVar(value="País"),  # grouping_var temporal, se actualizará después
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

        # Crear la instancia de ViewManager
        self.view_manager = ViewManager(
            self.main_frame,
            self.screen_width,
            self.screen_height,
            self.email_preview,
            self.exporter
        )

        # Frame para centrar el campo de entrada y el checkbox
        self.entry_frame = tk.Frame(self.main_frame)
        self.entry_frame.grid(row=2, column=0, pady=5, sticky="ew")
        tk.Label(self.entry_frame, text="Ingrese códigos de país, palabras clave o números de campaña (separados por coma):", fg="#23376D", font=("TkDefaultFont", 10, "bold")).pack()
        self.entry = tk.Entry(self.entry_frame, width=50)
        self.entry.pack(pady=5)
        # Deshabilitar el campo de entrada inicialmente, ya que el checkbox está marcado por defecto
        self.entry.config(state=tk.DISABLED)
        # Checkbox para analizar todas las campañas
        self.analyze_all_check = tk.Checkbutton(
            self.entry_frame,
            text="Analizar todas las campañas",
            variable=self.analyze_all_campaigns,
            fg="#23376D",
            font=("TkDefaultFont", 10, "bold"),
            command=self.toggle_entry_state
        )
        self.analyze_all_check.pack(pady=5)

        # Frame para centrar los botones
        self.buttons_frame = tk.Frame(self.main_frame)
        self.buttons_frame.grid(row=3, column=0, pady=10, sticky="ew")
        self.frame_botones = tk.Frame(self.buttons_frame)
        self.frame_botones.pack()
        self.btn_analizar = tk.Button(self.frame_botones, text="Analizar", 
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

        # Configurar la vista inicial para inicializar campanas_tabla
        self.grouping_var = tk.StringVar(value="Fecha")
        self.setup_metrics_view()

        # Crear la instancia de Analyzer después de inicializar campanas_tabla
        self.analyzer = Analyzer(
            self.campanas,
            self.last_results,
            self.resultados_tabla,
            self.resultados_label,
            self.entry,
            self.btn_analizar,
            self.btn_exportar,
            self.btn_nuevo_rango,
            self.root,
            self.email_preview,
            self.is_analysis_mode,
            self.setup_analysis_view,
            self.view_manager.filter_var,
            self.analyze_all_campaigns,
            self.campanas_tabla
        )

        # Configurar el comando del botón Analizar y el binding del Entry
        self.btn_analizar.config(command=self.analyzer.analizar)
        self.entry.bind("<Return>", lambda event: self.analyzer.analizar())

        self.root.update()
        self.root.lift()
        self.root.focus_set()
        self.root.after(100, self.entry.focus_set)

    def toggle_entry_state(self):
        """Habilita o deshabilita el campo de entrada según el estado del checkbox."""
        if self.analyze_all_campaigns.get():
            self.entry.config(state=tk.DISABLED)
        else:
            self.entry.config(state=tk.NORMAL)
            self.entry.focus_set()

    def setup_metrics_view(self):
        """Configura la vista inicial con solo la tabla de métricas."""
        self.view_manager.entry_frame = self.entry_frame
        self.view_manager.buttons_frame = self.buttons_frame
        self.view_manager.setup_metrics_view(
            self.entry_frame,
            self.buttons_frame,
            self.grouping_var,
            self.show_local_value,
            self.update_grouping,
            self.list_start_date,
            self.list_end_date
        )
        self.campanas_tabla = self.view_manager.campanas_tabla
        self.grand_total_tabla = self.view_manager.grand_total_tabla
        self.column_widths = self.view_manager.column_widths
        self.left_frame = self.view_manager.left_frame
        # Asegurarse de que self.analyzer exista antes de asignar
        if hasattr(self, 'analyzer'):
            self.analyzer.resultados_tabla = self.resultados_tabla
            self.analyzer.resultados_label = self.resultados_label
            self.analyzer.campanas_tabla = self.campanas_tabla
        self.email_preview.campanas_tabla = self.campanas_tabla
        self.exporter.campanas_tabla = self.campanas_tabla
        self.update_grouping(None)

    def setup_analysis_view(self):
        """Configura la vista con dos paneles: métricas a la izquierda y resultados a la derecha."""
        self.is_analysis_mode.set(True)
        self.view_manager.setup_analysis_view(
            self.grouping_var,
            self.show_local_value,
            self.update_grouping,
            self.cerrar_analisis,
            self.analyzer.apply_filter,
            self.list_start_date,
            self.list_end_date
        )
        self.campanas_tabla = self.view_manager.campanas_tabla
        self.grand_total_tabla = self.view_manager.grand_total_tabla
        self.column_widths = self.view_manager.column_widths
        self.left_frame = self.view_manager.left_frame
        self.resultados_tabla = self.view_manager.resultados_tabla
        self.resultados_label = self.view_manager.resultados_label
        self.analyzer.resultados_tabla = self.resultados_tabla
        self.analyzer.resultados_label = self.resultados_label
        self.analyzer.campanas_tabla = self.campanas_tabla
        self.email_preview.campanas_tabla = self.campanas_tabla
        self.exporter.campanas_tabla = self.campanas_tabla
        self.update_grouping(None)

    def cerrar_analisis(self):
        """Cierra el panel de análisis y restaura la vista de métricas."""
        self.is_analysis_mode.set(False)
        self.email_preview.is_analysis_mode = self.is_analysis_mode
        self.exporter.is_analysis_mode = self.is_analysis_mode
        self.last_results.clear()
        self.resultados_tabla = None
        self.email_preview.resultados_tabla = None
        self.exporter.resultados_tabla = None
        self.analyzer.resultados_tabla = None
        self.resultados_label = None
        self.email_preview.resultados_label = None
        self.analyzer.resultados_label = None
        self.analyze_all_campaigns.set(True)
        self.setup_metrics_view()
        self.toggle_entry_state()

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

    def update_grouping(self, event=None):
        """Función modificada para pasar view_manager a mostrar_campanas_en_tabla."""
        self.template_ids.clear()
        
        try:
            all_subtotals = mostrar_campanas_en_tabla(
                self.campanas, 
                self.campanas_tabla, 
                self.grouping_var.get(), 
                self.show_local_value.get(),
                template_ids_dict=self.template_ids,
                view_manager=self.view_manager  # PASAR VIEW_MANAGER
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

    def nuevo_rango(self):
        if self.webview_window:
            self.webview_window.destroy()
            self.webview_window = None
            self.email_preview.webview_window[0] = None

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
    app = None
    temp_app = ResultadosApp.__new__(ResultadosApp)
    temp_app.view_manager = ViewManager(None, 0, 0, None, None)

    campanas, error = obtener_campanas(list_start_date, list_end_date, update_text)
    if error:
        texto_resultados.delete(1.0, tk.END)
        texto_resultados.insert(tk.END, f"Error al cargar campañas: {error}\n")
        # Frame para centrar los botones
        buttons_frame = tk.Frame(root)
        buttons_frame.pack(pady=10)
        tk.Button(buttons_frame, text="Cerrar", command=lambda: [root.quit(), root.destroy()], 
                 bg="#23376D", fg="white", activebackground="#3A4F9A", 
                 activeforeground="white", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Nuevo rango de fecha", command=lambda: [root.quit(), root.destroy(), main()], 
                 bg="#23376D", fg="white", activebackground="#3A4F9A", 
                 activeforeground="white", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=5)
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
    main()