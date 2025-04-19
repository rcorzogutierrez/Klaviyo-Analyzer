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
from view_manager import ViewManager

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
        self.grouping_var = tk.StringVar(value="País")
        self.setup_metrics_view()

        self.root.update()
        self.root.lift()
        self.root.focus_set()
        self.root.after(100, self.entry.focus_set)

    def setup_metrics_view(self):
        """Configura la vista inicial con solo la tabla de métricas."""
        self.view_manager.entry_frame = self.entry_frame
        self.view_manager.buttons_frame = self.buttons_frame
        self.view_manager.setup_metrics_view(
            self.entry_frame,
            self.buttons_frame,
            self.grouping_var,
            self.show_local_value,
            self.update_grouping
        )
        self.campanas_tabla = self.view_manager.campanas_tabla
        self.grand_total_tabla = self.view_manager.grand_total_tabla
        self.column_widths = self.view_manager.column_widths
        self.left_frame = self.view_manager.left_frame
        self.update_grouping(None)

    def setup_analysis_view(self):
        """Configura la vista con dos paneles: métricas a la izquierda y resultados a la derecha."""
        self.is_analysis_mode = True
        self.view_manager.setup_analysis_view(
            self.grouping_var,
            self.show_local_value,
            self.update_grouping,
            self.cerrar_analisis
        )
        self.campanas_tabla = self.view_manager.campanas_tabla
        self.grand_total_tabla = self.view_manager.grand_total_tabla
        self.column_widths = self.view_manager.column_widths
        self.left_frame = self.view_manager.left_frame
        self.resultados_tabla = self.view_manager.resultados_tabla
        self.resultados_label = self.view_manager.resultados_label
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