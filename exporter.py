import zipfile
from tkinter import filedialog, messagebox
import io
import csv
from datetime import datetime

class Exporter:
    def __init__(self, campanas, campanas_tabla, grouping_var, last_results, is_analysis_mode, resultados_tabla):
        self.campanas = campanas
        self.campanas_tabla = campanas_tabla
        self.grouping_var = grouping_var
        self.last_results = last_results
        self.is_analysis_mode = is_analysis_mode
        self.resultados_tabla = resultados_tabla

    def exportar(self):
        default_filename = f"results_{datetime.now().strftime('%Y-%m-%d')}.zip"
        folder = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")],
            title="Guardar archivo ZIP",
            initialfile=default_filename
        )
        if not folder:
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_tabla.delete(*self.resultados_tabla.get_children())
                self.resultados_tabla.insert("", "end", values=("", "", "Exportación cancelada por el usuario.", "", ""))
            else:
                messagebox.showinfo("Información", "Exportación cancelada por el usuario.")
            return

        if self.is_analysis_mode and self.resultados_tabla:
            self.resultados_tabla.delete(*self.resultados_tabla.get_children())

        try:
            with zipfile.ZipFile(folder, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Exportar campañas si existen
                if self.campanas:
                    campaigns_filename = f"campaigns_analysis_{datetime.now().strftime('%Y-%m-%d')}_{self.grouping_var.get().lower()}.csv"
                    csv_content = io.StringIO()
                    fieldnames = [
                        "#", "Nombre", "Fecha de Envío", "Open Rate", "Click Rate", "Recibidos",
                        "Unique Orders", "Total Value (USD)", "Total Value (Local)", "Per Recipient",
                        "Order Count", "Subject Line", "Preview Text"
                    ]
                    writer = csv.DictWriter(csv_content, fieldnames=fieldnames)
                    writer.writeheader()

                    last_fecha = None
                    for item in self.campanas_tabla.get_children():
                        values = self.campanas_tabla.item(item, "values")

                        # Línea de fecha o prefijo (grupo)
                        if all(v == "" for v in values[1:]) and values[0]:
                            if values[0] != last_fecha and values[0].count("-") == 2:
                                writer.writerow({})
                                last_fecha = values[0]
                            writer.writerow({fieldnames[0]: values[0]})
                            continue

                        # Línea de subtotal
                        if values[1] == "Subtotal":
                            row = dict(zip(fieldnames, values))
                            writer.writerow(row)
                            continue

                        # Línea de campaña (real)
                        try:
                            int(values[0])
                            row = dict(zip(fieldnames, values))
                            writer.writerow(row)
                        except (ValueError, IndexError):
                            continue

                    zipf.writestr(campaigns_filename, csv_content.getvalue())
                    if self.is_analysis_mode and self.resultados_tabla:
                        self.resultados_tabla.insert("", "end", values=("", "", f"Archivo CSV creado: {campaigns_filename}", "", ""))
                    else:
                        messagebox.showinfo("Información", f"Archivo CSV creado: {campaigns_filename}")

                # Exportar los resultados del análisis si existen
                if self.last_results:
                    for (campaign_name, send_date), totales in self.last_results.items():
                        filename = f"{campaign_name.replace(' ', '_')}_{send_date}_results.csv"
                        csv_content = io.StringIO()
                        fieldnames = ['URL', 'Clics Totales', 'Clics Únicos']
                        writer = csv.DictWriter(csv_content, fieldnames=fieldnames)
                        writer.writeheader()
                        for url, data in totales.items():
                            writer.writerow({'URL': url, 'Clics Totales': data['count'], 'Clics Únicos': data['unique']})
                        zipf.writestr(filename, csv_content.getvalue())
                        if self.is_analysis_mode and self.resultados_tabla:
                            self.resultados_tabla.insert("", "end", values=("", "", f"Archivo CSV creado: {filename}", "", ""))
                        else:
                            messagebox.showinfo("Información", f"Archivo CSV creado: {filename}")

                # Mensaje de éxito
                message = f"Exportación exitosa. Resultados comprimidos en: {folder}"
                if self.is_analysis_mode and self.resultados_tabla:
                    self.resultados_tabla.insert("", "end", values=("", "", message, "", ""))
                else:
                    messagebox.showinfo("Información", message)

        except Exception as e:
            message = f"Error al exportar: {e}"
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_tabla.insert("", "end", values=("", "", message, "", ""))
            else:
                messagebox.showerror("Error", message)