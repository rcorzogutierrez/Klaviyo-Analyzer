import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
from datetime import datetime
from campaign_logic import seleccionar_campanas, query_metric_aggregates_post

class Analyzer:
    def __init__(self, campanas, last_results, resultados_tabla, resultados_label, entry, 
                 btn_analizar, btn_exportar, btn_nuevo_rango, root, email_preview, 
                 is_analysis_mode, setup_analysis_view_callback):
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

        self.resultados_tabla.delete(*self.resultados_tabla.get_children())
        self.resultados_tabla.insert("", "end", values=("", "", "Buscando información...", "", ""))
        
        self.entry.config(state=tk.DISABLED)
        self.btn_analizar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_exportar.config(state=tk.DISABLED, bg="#A9A9A9")
        self.btn_nuevo_rango.config(state=tk.DISABLED, bg="#A9A9A9")

        self.resultados_label.config(text=f"Resultados del análisis: {input_str}", font=("TkDefaultFont", 12, "bold"), fg="#23376D")
        self.email_preview.resultados_label = self.resultados_label

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
        self.btn_exportar.config(state=tk.NORMAL, bg="#23376D")
        self.btn_nuevo_rango.config(state=tk.NORMAL, bg="#23376D")

        self.entry.delete(0, tk.END)
        self.entry.focus_set()