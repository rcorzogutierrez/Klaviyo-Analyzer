import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
from datetime import datetime
from campaign_logic import seleccionar_campanas, query_metric_aggregates_post
import threading

class Analyzer:
    def __init__(self, campanas, last_results, resultados_tabla, resultados_label, entry, 
                 btn_analizar, btn_exportar, btn_nuevo_rango, root, email_preview, 
                 is_analysis_mode, setup_analysis_view_callback, filter_var):
        self.campanas = campanas
        self.last_results = last_results
        self.resultados_tabla = resultados_tabla
        self.resultados_label = resultados_label
        self.entry = entry
        self.btn_analizar = btn_analizar
        self.btn_exportar = btn_exportar
        self.btn_nuevo_rango = btn_nuevo_rango
        self.root = root
        self.email_preview = email_preview
        self.is_analysis_mode = is_analysis_mode
        self.setup_analysis_view_callback = setup_analysis_view_callback
        self.filter_var = filter_var  # Variable para rastrear la selección del filtro
        self.all_click_data = {}  # Almacenar todos los datos de clics para filtrar

    def analizar(self):
        # Verificar si estamos en modo análisis; si no, cambiar a la vista de análisis
        if not self.is_analysis_mode.get():
            self.setup_analysis_view_callback()

        # Verificar que resultados_tabla exista después de setup_analysis_view
        if not self.resultados_tabla:
            messagebox.showerror("Error", "No se pudo inicializar la tabla de resultados. Por favor, intenta de nuevo.")
            return

        input_str = self.entry.get().strip()
        if not input_str:
            messagebox.showinfo("Información", "Por favor, ingrese códigos de país, palabras clave o números de campaña.")
            return

        # Deshabilitar widgets para evitar interacciones durante el análisis
        self.entry.config(state=tk.DISABLED)
        self.btn_analizar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_exportar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_nuevo_rango.config(state=tk.DISABLED, bg="#A9A9A9")

        # Mostrar mensaje inicial de "Buscando información..."
        self.resultados_tabla.delete(*self.resultados_tabla.get_children())
        self.resultados_tabla.insert("", "end", values=("", "", "Buscando información...", "", ""))
        
        self.resultados_label.config(text=f"Resultados del análisis: {input_str}", font=("TkDefaultFont", 12, "bold"), fg="#23376D")
        self.email_preview.resultados_label = self.resultados_label

        self.root.update()

        # Ejecutar el análisis en un hilo separado
        analysis_thread = threading.Thread(target=self._run_analysis, args=(input_str,))
        analysis_thread.start()

    def _run_analysis(self, input_str):
        # Realizar el análisis en un hilo separado
        seleccionados = seleccionar_campanas(self.campanas, input_str)
        if not seleccionados:
            self._update_ui_no_campaigns()
        else:
            self.last_results.clear()
            self.all_click_data.clear()
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
                        # Almacenar datos para el filtro
                        if send_date not in self.all_click_data:
                            self.all_click_data[send_date] = {}
                        self.all_click_data[send_date][campaign_name] = (total_clicks, totales)
                    else:
                        resultados_por_fecha_pais[send_date][campaign_name].append(("No se encontraron clics para esta campaña.", None, total_clicks))

            # Actualizar la interfaz desde el hilo principal
            self._update_ui_with_results(resultados_por_fecha_pais)

        # Rehabilitar widgets desde el hilo principal
        self.root.after(0, self._finalize_ui)

    def _update_ui_no_campaigns(self):
        # Actualizar la interfaz cuando no hay campañas seleccionadas
        def update():
            self.resultados_tabla.delete(*self.resultados_tabla.get_children())
            self.resultados_tabla.insert("", "end", values=("", "", "No se seleccionaron campañas.", "", ""))
        self.root.after(0, update)

    def _update_ui_with_results(self, resultados_por_fecha_pais):
        # Actualizar la interfaz con los resultados del análisis aplicando el filtro
        def update():
            self.apply_filter()
        self.root.after(0, update)

    def extract_sku_or_category_id(self, url, filter_type):
        """
        Extrae el SKU o ID Categoría de la URL según el filtro seleccionado, deteniéndose antes del '?' y preservando mayúsculas.

        Args:
            url (str): La URL de la que extraer el valor.
            filter_type (str): El tipo de filtro ("Producto" o "Categoría").

        Returns:
            str: El SKU o ID Categoría extraído, o "" si no se encuentra.
        """
        # Usar una versión en minúsculas para las comparaciones, pero la original para extraer el valor
        url_lower = url.lower()
        url_original = url  # Mantener la URL original para preservar mayúsculas

        # Dividir la URL antes del '?' para ignorar parámetros de consulta
        url_lower = url_lower.split("?")[0]
        url_original = url_original.split("?")[0]

        if filter_type == "Producto":
            # Buscar /producto/descripcion-del-producto/SKU
            if "/producto/" in url_lower:
                parts = url_lower.split("/producto/")[1].split("/")
                if len(parts) >= 2:  # Asegurarse de que hay al menos descripción y SKU
                    # Usar la URL original para extraer el SKU con mayúsculas preservadas
                    original_parts = url_original.split("/producto/")[1].split("/")
                    return original_parts[-1]  # El último elemento es el SKU
            elif "/product/" in url_lower:
                parts = url_lower.split("/product/")[1].split("/")
                if len(parts) >= 2:
                    original_parts = url_original.split("/product/")[1].split("/")
                    return original_parts[-1]
        elif filter_type == "Categoría":
            # Buscar /categoria/descripcion-del-producto/ID Categoria
            if "/categoria/" in url_lower:
                parts = url_lower.split("/categoria/")[1].split("/")
                if len(parts) >= 2:
                    original_parts = url_original.split("/categoria/")[1].split("/")
                    return original_parts[-1]  # El último elemento es el ID Categoría
            elif "/category/" in url_lower:
                parts = url_lower.split("/category/")[1].split("/")
                if len(parts) >= 2:
                    original_parts = url_original.split("/category/")[1].split("/")
                    return original_parts[-1]
        return ""

    def apply_filter(self, event=None):
        """Filtra los datos de clics según la selección del filtro y actualiza la tabla de resultados."""
        if not self.resultados_tabla:
            return

        self.resultados_tabla.delete(*self.resultados_tabla.get_children())
        filter_type = self.filter_var.get()

        filtered_urls_count = 0

        for fecha in sorted(self.all_click_data.keys()):
            self.resultados_tabla.insert("", "end", values=("", "", f"Fecha de envío: {fecha}", "", ""), tags=("bold",))
            campañas_ordenadas = {}
            for campaign_name, (total_clicks, totales) in self.all_click_data[fecha].items():
                campañas_ordenadas[campaign_name] = total_clicks

            for campaign_name in sorted(campañas_ordenadas, key=lambda x: campañas_ordenadas[x], reverse=True):
                total_clicks, totales = self.all_click_data[fecha][campaign_name]
                todas_las_urls = []
                for url, data in totales.items():
                    url_lower = url.lower()
                    # Aplicar el filtro
                    if filter_type == "Todos":
                        todas_las_urls.append((url, data["count"], data["unique"]))
                    elif filter_type == "Producto":
                        if "/producto/" in url_lower or "/product/" in url_lower:
                            todas_las_urls.append((url, data["count"], data["unique"]))
                    elif filter_type == "Categoría":
                        if "/categoria/" in url_lower or "/category/" in url_lower:
                            todas_las_urls.append((url, data["count"], data["unique"]))

                # Mostrar la campaña incluso si no tiene URLs que cumplan con el filtro
                self.resultados_tabla.insert("", "end", values=(campaign_name, total_clicks, "", "", ""))
                if todas_las_urls:
                    todas_las_urls.sort(key=lambda x: x[1], reverse=True)
                    for url, clics_totales, clics_unicos in todas_las_urls:
                        # Extraer SKU o ID Categoría si aplica
                        extra_value = self.extract_sku_or_category_id(url, filter_type) if filter_type in ["Producto", "Categoría"] else ""
                        if filter_type in ["Producto", "Categoría"]:
                            self.resultados_tabla.insert("", "end", values=("", "", url, clics_totales, clics_unicos, extra_value))
                        else:
                            self.resultados_tabla.insert("", "end", values=("", "", url, clics_totales, clics_unicos))
                        filtered_urls_count += 1
                else:
                    # Mostrar un mensaje si no hay URLs que cumplan con el filtro
                    if filter_type == "Producto":
                        self.resultados_tabla.insert("", "end", values=("", "", "No se encontraron productos en esta campaña.", "", ""))
                    elif filter_type == "Categoría":
                        self.resultados_tabla.insert("", "end", values=("", "", "No se encontraron categorías en esta campaña.", "", ""))
                
                self.resultados_tabla.insert("", "end", values=("", "", "", "", ""))

        self.resultados_tabla.insert("", "end", values=("", "", "Análisis completado.", "", ""))
        self.resultados_label.config(text=f"Resultados del análisis: {filtered_urls_count} enlaces analizados")

    def _finalize_ui(self):
        # Rehabilitar widgets y limpiar el campo de entrada
        self.entry.config(state=tk.NORMAL)
        self.btn_analizar.config(state=tk.NORMAL, bg="#23376D")
        self.btn_exportar.config(state=tk.NORMAL, bg="#23376D")
        self.btn_nuevo_rango.config(state=tk.NORMAL, bg="#23376D")
        self.entry.delete(0, tk.END)
        self.entry.focus_set()