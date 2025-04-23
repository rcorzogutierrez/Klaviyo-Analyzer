import requests
import webview
from config import HEADERS_KLAVIYO

class EmailPreview:
    def __init__(self, webview_window, campanas_tabla, template_ids, is_analysis_mode, resultados_tabla, resultados_label, screen_width, screen_height, root):
        self.webview_window = [webview_window]  # Usamos una lista para poder modificar la referencia
        self.campanas_tabla = campanas_tabla
        self.template_ids = template_ids
        self.is_analysis_mode = is_analysis_mode
        self.resultados_tabla = resultados_tabla
        self.resultados_label = resultados_label
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.root = root
        self.original_table_content = []  # Para almacenar el contenido original de resultados_tabla

    def preview_template(self, event):
        # Cerrar la ventana de previsualización si ya está abierta
        if self.webview_window[0]:
            self.webview_window[0].destroy()
            self.webview_window[0] = None

        self.root.update()
        current_state = self.root.state()

        # Obtener el elemento seleccionado en la tabla
        selected_item = self.campanas_tabla.selection()
        if not selected_item:
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_label.config(text="Previsualización del Template: Error")
            return

        # Obtener el item_id de la fila seleccionada
        item_id = selected_item[0]
        # Obtener los valores de la fila seleccionada
        item = self.campanas_tabla.item(item_id)
        values = item["values"]
        if not values or len(values) < 13:  # 13 columnas (índices 0-12)
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_label.config(text="Previsualización del Template: Error")
            return

        # Obtener el template_id del diccionario interno
        template_id = self.template_ids.get(item_id)
        campaign_name = values[1]  # Nombre de la campaña está en el índice 1
        if not template_id:
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_label.config(text="Previsualización del Template: No disponible")
            return

        # Determinar el país a partir del nombre de la campaña
        partes = campaign_name.split("_")
        country = partes[-1].strip().upper() if len(partes) > 1 else "US"

        # Configurar la solicitud a la API de Klaviyo
        render_url = "https://a.klaviyo.com/api/template-render"
        headers = HEADERS_KLAVIYO.copy()
        headers["revision"] = "2023-12-15"

        data = {
            "data": {
                "type": "template",
                "id": template_id,
                "attributes": {
                    "context": {
                        "person": {
                            "country": country
                        }
                    }
                }
            }
        }

        try:
            response = requests.post(render_url, json=data, headers=headers, timeout=30)
            response.raise_for_status()  # Lanza una excepción si hay un error HTTP
            if response.status_code == 200:
                html_content = response.json().get("data", {}).get("attributes", {}).get("html", "")
                if html_content:
                    webview_width = int(self.screen_width * 0.6)
                    webview_height = int(self.screen_height * 0.6)
                    self.webview_window[0] = webview.create_window(
                        f"Previsualización del Template: {campaign_name} (País: {country})",
                        html=html_content,
                        width=webview_width,
                        height=webview_height
                    )
                    webview.start(gui='tk')
                    if self.is_analysis_mode and self.resultados_label:
                        self.resultados_label.config(text=f"Previsualización del Template: {campaign_name} (País: {country})")
                else:
                    if self.is_analysis_mode and self.resultados_label:
                        self.resultados_label.config(text="Previsualización del Template: Error")
            else:
                if self.is_analysis_mode and self.resultados_label:
                    self.resultados_label.config(text="Previsualización del Template: Error")
        except requests.exceptions.RequestException as e:
            if self.is_analysis_mode and self.resultados_label:
                self.resultados_label.config(text="Previsualización del Template: Error")
            print(f"Error al renderizar el template: {str(e)}")  # Para depuración

        self.root.update()
        if current_state == 'zoomed':
            self.root.state('zoomed')
        else:
            self.root.geometry(f"{self.screen_width}x{self.screen_height}")

    def preview_url(self, url):
        """Carga la URL directamente en el visualizador integrado para que maneje estilos y JavaScript."""
        # Cerrar la ventana de previsualización si ya está abierta
        if self.webview_window[0]:
            self.webview_window[0].destroy()
            self.webview_window[0] = None

        self.root.update()
        current_state = self.root.state()

        if not url:
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_label.config(text="Previsualización de la URL: Error")
                self.resultados_tabla.delete(*self.resultados_tabla.get_children())
                self.resultados_tabla.insert("", "end", values=("", "", "No se proporcionó una URL válida.", "", ""))
            return

        # Copiar la URL al portapapeles
        self.root.clipboard_clear()
        self.root.clipboard_append(url)

        # Guardar el contenido actual de resultados_tabla
        self.original_table_content = []
        for item in self.resultados_tabla.get_children():
            values = self.resultados_tabla.item(item, "values")
            tags = self.resultados_tabla.item(item, "tags")
            self.original_table_content.append((values, tags))

        # Mostrar mensaje temporal sin limpiar la tabla completamente
        if self.is_analysis_mode and self.resultados_tabla:
            self.resultados_label.config(text=f"URL copiada: {url}")
            self.resultados_tabla.delete(*self.resultados_tabla.get_children())
            self.resultados_tabla.insert("", "end", values=("", "", "Cargando URL en el visualizador...", "", ""))

        # Cargar la URL directamente en pywebview
        try:
            webview_width = int(self.screen_width * 0.6)
            webview_height = int(self.screen_height * 0.6)
            self.webview_window[0] = webview.create_window(
                f"Previsualización de la URL: {url}",
                url=url,
                width=webview_width,
                height=webview_height
            )
            webview.start(gui='tk')

            # Restaurar el contenido original de la tabla inmediatamente después de abrir la ventana
            if self.is_analysis_mode and self.resultados_tabla and self.original_table_content:
                self.resultados_tabla.delete(*self.resultados_tabla.get_children())
                for values, tags in self.original_table_content:
                    self.resultados_tabla.insert("", "end", values=values, tags=tags)
                self.resultados_label.config(text="Resultados del análisis: URL copiada al portapapeles")

        except Exception as e:
            if self.is_analysis_mode and self.resultados_tabla:
                self.resultados_label.config(text="Previsualización de la URL: Error")
                self.resultados_tabla.delete(*self.resultados_tabla.get_children())
                self.resultados_tabla.insert("", "end", values=("", "", f"Error al cargar la URL: {str(e)}", "", ""))
                # Restaurar el contenido original en caso de error
                for values, tags in self.original_table_content:
                    self.resultados_tabla.insert("", "end", values=values, tags=tags)
                self.resultados_label.config(text="Resultados del análisis: URL copiada al portapapeles")
            print(f"Error al cargar la URL: {str(e)}")  # Para depuración

        self.root.update()
        if current_state == 'zoomed':
            self.root.state('zoomed')
        else:
            self.root.geometry(f"{self.screen_width}x{self.screen_height}")