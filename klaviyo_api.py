# klaviyo_api.py
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from config import HEADERS_KLAVIYO, KLAVIYO_URLS  # Importar solo lo necesario

def get_campaign_metrics(start_date, end_date, conversion_metric_id, update_callback=None):
    """
    Obtiene métricas de campañas (open rate, click rate, delivered) desde la API de Klaviyo.

    Args:
        start_date (str): Fecha de inicio en formato "YYYY-MM-DD".
        end_date (str): Fecha de fin en formato "YYYY-MM-DD".
        conversion_metric_id (str): ID de la métrica de conversión en Klaviyo.
        update_callback (callable, optional): Función para actualizar el estado en la UI.

    Returns:
        list: Lista de resultados de métricas de campañas.
    """
    fecha_inicio = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    fecha_fin = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc, hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')

    data = {
        "data": {
            "type": "campaign-values-report",
            "attributes": {
                "timeframe": {"start": fecha_inicio, "end": fecha_fin},
                "conversion_metric_id": conversion_metric_id,
                "statistics": ["open_rate", "click_rate", "delivered", "delivery_rate"] 
            }
        }
    }
    all_data = []
    url = KLAVIYO_URLS["CAMPAIGN_VALUES_REPORT"]
    page_count = 0
    while url:
        response = requests.post(url, headers=HEADERS_KLAVIYO, json=data, timeout=30)
        if response.status_code == 200:
            data = response.json()
            all_data.extend(data['data']['attributes']['results'])
            page_count += 1
            if update_callback:
                update_callback(f"Página {page_count} obtenida")
            url = data.get('links', {}).get('next')
            data = None  # No enviar parámetros adicionales en las siguientes solicitudes
        else:
            if update_callback:
                update_callback(f"Error: {response.status_code} - {response.text}")
            break
    if update_callback:
        update_callback(f"Total de páginas obtenidas: {page_count}")
    return all_data

def get_campaign_details(campaign_id, cache, update_callback=None):
    """
    Obtiene detalles de una campaña específica desde la API de Klaviyo.

    Args:
        campaign_id (str): ID de la campaña en Klaviyo.
        cache (dict): Diccionario para almacenar los detalles en caché.
        update_callback (callable, optional): Función para actualizar el estado en la UI.

    Returns:
        tuple: (campaign_name, send_time, subject_line, preview_text, template_id)
    """
    if campaign_id in cache:
        return cache[campaign_id]
    url = f"{KLAVIYO_URLS['CAMPAIGN_DETAILS']}{campaign_id}/"
    while True:
        response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
        if response.status_code == 200:
            campaign_data = response.json()
            campaign_name = campaign_data['data']['attributes'].get('name', f"Campaign {campaign_id}")
            send_time = campaign_data['data']['attributes'].get('send_time', 'N/A')
            if send_time != 'N/A':
                send_time = datetime.fromisoformat(send_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')

            # Obtener el subject line, preview text y template_id desde los mensajes de la campaña
            subject_line, preview_text, template_id = get_campaign_message_subject(campaign_data, update_callback)

            if update_callback:
                update_callback(f"Obteniendo detalles de la campaña {campaign_name}")
            cache[campaign_id] = (campaign_name, send_time, subject_line, preview_text, template_id)
            return campaign_name, send_time, subject_line, preview_text, template_id
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 17))
            if update_callback:
                update_callback(f"Solicitud limitada para ID {campaign_id}. Esperando {retry_after} segundos antes de reintentar")
            time.sleep(retry_after)
        else:
            if update_callback:
                update_callback(f"Error al obtener la campaña {campaign_id}: {response.status_code} - {response.text}")
            return f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None

def get_campaign_message_subject(campaign_data, update_callback=None):
    """
    Obtiene el subject line, preview text y template ID de una campaña desde los datos de la API.

    Args:
        campaign_data (dict): Datos de la campaña obtenidos de la API.
        update_callback (callable, optional): Función para actualizar el estado en la UI.

    Returns:
        tuple: (subject_line, preview_text, template_id)
            - subject_line (str): Asunto del mensaje.
            - preview_text (str): Texto de vista previa del mensaje.
            - template_id (str or None): ID del template asociado, o None si no existe.
    """
    if 'relationships' in campaign_data['data'] and 'campaign-messages' in campaign_data['data']['relationships']:
        message_id = campaign_data['data']['relationships']['campaign-messages']['data'][0]['id']
        url = f"{KLAVIYO_URLS['CAMPAIGN_MESSAGES']}{message_id}/"
        
        max_retries = 5
        delay = 1
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    message_data = response.json()
                    subject = message_data['data']['attributes']['definition']['content'].get('subject', "No Subject Line")
                    preview = message_data['data']['attributes']['definition']['content'].get('preview_text', "No Preview Text")
                    # Obtener el template_id
                    try:
                        template_id = message_data['data']['relationships']['template']['data']['id']
                    except (KeyError, TypeError):
                        template_id = None  # Si no hay template asociado
                    if update_callback:
                        update_callback(f"Obteniendo subject, preview y template para mensaje {message_id}")
                    return subject, preview, template_id
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 17))
                    if update_callback:
                        update_callback(f"Solicitud limitada para mensaje {message_id}. Esperando {retry_after} segundos antes de reintentar")
                    time.sleep(retry_after)
                else:
                    if update_callback:
                        update_callback(f"Error al obtener el mensaje {message_id}: {response.status_code} - {response.text}")
                    return "No Subject Line", "No Preview Text", None
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Backoff exponencial
                    continue
                if update_callback:
                    update_callback(f"Error inesperado al obtener el mensaje {message_id} tras {max_retries} intentos: {str(e)}")
                return "No Subject Line", "No Preview Text", None
    
    if update_callback:
        update_callback(f"Error: No se encontraron mensajes para la campaña")
    return "No Subject Line", "No Preview Text", None

def preload_campaign_details(campaign_ids, cache, update_callback=None):
    """
    Precarga los detalles de múltiples campañas en un caché.

    Args:
        campaign_ids (list): Lista de IDs de campañas.
        cache (dict): Diccionario para almacenar los detalles en caché.
        update_callback (callable, optional): Función para actualizar el estado en la UI.
    """
    count = 0
    total_campaigns = len(campaign_ids)
    if update_callback:
        update_callback(f"Precargando detalles de las campañas (0/{total_campaigns})")
    for campaign_id in campaign_ids:
        if campaign_id not in cache:
            count += 1
            if update_callback:
                update_callback(f"Precargando detalles de las campañas ({count}/{total_campaigns})")
            get_campaign_details(campaign_id, cache, update_callback)
    if update_callback:
        update_callback("Precarga de detalles de campañas completada")

def query_metric_aggregates_post(campaign_id, start_date_val, end_date_val):
    """
    Consulta la API de Klaviyo para obtener métricas agregadas (clics totales y únicos por URL)
    para una campaña específica en un rango de fechas.

    Args:
        campaign_id (str): ID de la campaña en Klaviyo.
        start_date_val (str): Fecha de inicio en formato "YYYY-MM-DD" o "YYYY-MM-DD HH:MM:SS".
        end_date_val (str): Fecha de fin en formato "YYYY-MM-DD" o "YYYY-MM-DD HH:MM:SS".

    Returns:
        tuple: (aggregated_data, error)
            - aggregated_data: Datos agregados de la API si la solicitud es exitosa.
            - error: Mensaje de error si la solicitud falla, None si no hay error.
    """
    url = KLAVIYO_URLS["METRIC_AGGREGATES"]

    # Simplificar start_date_val a solo la fecha (YYYY-MM-DD) si incluye hora
    try:
        dt_start = datetime.strptime(start_date_val, "%Y-%m-%d %H:%M:%S")
        start_date_val = dt_start.strftime("%Y-%m-%d")
    except ValueError:
        # Si ya está en formato YYYY-MM-DD, no hacer nada
        pass

    # Usar la fecha y hora actual en UTC como fecha final
    dt_end = datetime.now(timezone.utc)  # Usar la fecha y hora actual en UTC
    next_day = (dt_end + timedelta(days=1)).strftime("%Y-%m-%d")

    payload = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "interval": "day",
                "page_size": 500,
                "timezone": "UTC",
                "measurements": ["count", "unique"],
                "by": ["URL"],
                "filter": [
                    f"greater-or-equal(datetime,{start_date_val}T00:00:00Z)",
                    f"less-than(datetime,{next_day}T00:00:00Z)",
                    f"equals($message,'{campaign_id}')"
                ],
                "metric_id": "SCJBvM"
            }
        }
    }

    max_retries = 5
    delay = 1
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=HEADERS_KLAVIYO, data=json.dumps(payload), timeout=30)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 17))
                time.sleep(retry_after)
                continue
            elif response.status_code == 400:
                error_detail = response.json().get('errors', [{'id': 'unknown_error'}])
                error_id = error_detail[0].get('id', 'unknown_error')
                return None, f"Error 400 en aggregates (POST): ID de error - {error_id}. Verifica el campaign_id '{campaign_id}', fechas, o filtros en Klaviyo."
            elif response.status_code != 200:
                return None, f"Error en aggregates (POST): {response.status_code} - {response.text}"
            else:
                aggregated_data = response.json()
                return aggregated_data, None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # Backoff exponencial
                continue
            return None, f"Error inesperado en aggregates (POST) tras {max_retries} intentos: {str(e)}"

    return None, "Se alcanzó el número máximo de reintentos debido a límites de tasa (429)."