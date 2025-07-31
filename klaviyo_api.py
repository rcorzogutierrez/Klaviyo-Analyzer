# klaviyo_api.py
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from config import HEADERS_KLAVIYO, KLAVIYO_URLS  # Importar solo lo necesario

# Modificaciones necesarias en klaviyo_api.py

def get_campaign_audiences(campaign_data, update_callback=None):
    """
    Extrae información de audiencias (listas y segmentos) de los datos de campaña.

    Args:
        campaign_data (dict): Datos de la campaña obtenidos de la API.
        update_callback (callable, optional): Función para actualizar el estado en la UI.

    Returns:
        str: Información formateada de las audiencias incluidas y excluidas con nombres.
    """
    try:
        # Obtener audiencias desde los atributos de la campaña
        audiences = campaign_data['data']['attributes'].get('audiences', {})
        
        if not audiences:
            return "N/A"
            
        included = audiences.get('included', [])
        excluded = audiences.get('excluded', [])
        
        # Formatear la información con nombres reales
        result_parts = []
        
        if included:
            # Obtener nombres de audiencias incluidas
            included_names = get_audience_names(included, update_callback)
            if included_names:
                # Mostrar solo los primeros 2 nombres completos para evitar texto muy largo
                included_display = included_names[:2]
                if len(included) > 2:
                    included_display.append(f"+{len(included) - 2}")
                result_parts.append(f"Inc: {', '.join(included_display)}")
        
        if excluded:
            # Obtener nombres de audiencias excluidas
            excluded_names = get_audience_names(excluded, update_callback)
            if excluded_names:
                # Mostrar solo los primeros 2 nombres completos
                excluded_display = excluded_names[:2]
                if len(excluded) > 2:
                    excluded_display.append(f"+{len(excluded) - 2}")
                result_parts.append(f"Exc: {', '.join(excluded_display)}")
        
        return "; ".join(result_parts) if result_parts else "N/A"
        
    except (KeyError, TypeError) as e:
        if update_callback:
            update_callback(f"Error al obtener audiencias: {str(e)}")
        return "N/A"

def get_audience_names(audience_ids, update_callback=None):
    """
    Obtiene los nombres de las audiencias basándose en sus IDs.
    
    Args:
        audience_ids (list): Lista de IDs de audiencias.
        update_callback (callable, optional): Función para actualizar el estado en la UI.
    
    Returns:
        list: Lista de nombres de audiencias.
    """
    names = []
    
    # Limitar a 3 audiencias para evitar demasiadas llamadas a la API
    for audience_id in audience_ids[:3]:
        try:
            # Primero intentar obtener como lista
            url = f"{KLAVIYO_URLS['LISTS']}{audience_id}/"
            response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                name = data['data']['attributes'].get('name', f"List-{audience_id[:8]}")
                names.append(name)
                continue
            elif response.status_code == 429:
                # Manejar rate limiting
                retry_after = int(response.headers.get('Retry-After', 10))
                if update_callback:
                    update_callback(f"Rate limit alcanzado. Esperando {retry_after} segundos...")
                time.sleep(retry_after)
                # Reintentar la misma solicitud
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    name = data['data']['attributes'].get('name', f"List-{audience_id[:8]}")
                    names.append(name)
                    continue
            
            # Si no es una lista, intentar como segmento
            url = f"{KLAVIYO_URLS['SEGMENTS']}{audience_id}/"
            response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                name = data['data']['attributes'].get('name', f"Segment-{audience_id[:8]}")
                names.append(name)
            elif response.status_code == 429:
                # Manejar rate limiting para segmentos
                retry_after = int(response.headers.get('Retry-After', 10))
                if update_callback:
                    update_callback(f"Rate limit alcanzado. Esperando {retry_after} segundos...")
                time.sleep(retry_after)
                # Reintentar la misma solicitud
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    name = data['data']['attributes'].get('name', f"Segment-{audience_id[:8]}")
                    names.append(name)
                else:
                    names.append(f"ID-{audience_id[:8]}")
            else:
                names.append(f"ID-{audience_id[:8]}")
                
        except Exception as e:
            if update_callback:
                update_callback(f"Error al obtener nombre de audiencia {audience_id}: {str(e)}")
            names.append(f"ID-{audience_id[:8]}")
            
        # Pequeña pausa entre solicitudes para evitar rate limiting
        time.sleep(0.1)
    
    # Si hay más de 3 audiencias, añadir indicador
    if len(audience_ids) > 3:
        names.append(f"+{len(audience_ids) - 3} más")
    
    return names

# Modificación en get_campaign_details para usar cache de audiencias
def get_campaign_details(campaign_id, cache, update_callback=None, audience_cache=None):
    """
    Obtiene detalles de una campaña específica desde la API de Klaviyo.

    Args:
        campaign_id (str): ID de la campaña en Klaviyo.
        cache (dict): Diccionario para almacenar los detalles en caché.
        update_callback (callable, optional): Función para actualizar el estado en la UI.
        audience_cache (dict, optional): Cache de nombres de audiencias.

    Returns:
        tuple: (campaign_name, send_time, subject_line, preview_text, template_id, audiences_info)
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

            # Obtener información de audiencias con nombres si hay cache disponible
            if audience_cache:
                audiences_info = get_campaign_audiences_with_cache(campaign_data, audience_cache, update_callback)
            else:
                audiences_info = get_campaign_audiences(campaign_data, update_callback)

            if update_callback:
                update_callback(f"Obteniendo detalles de la campaña {campaign_name}")
            
            result = (campaign_name, send_time, subject_line, preview_text, template_id, audiences_info)
            cache[campaign_id] = result
            return result
            
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 17))
            if update_callback:
                update_callback(f"Solicitud limitada para ID {campaign_id}. Esperando {retry_after} segundos antes de reintentar")
            time.sleep(retry_after)
        else:
            if update_callback:
                update_callback(f"Error al obtener la campaña {campaign_id}: {response.status_code} - {response.text}")
            return f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A"

def get_campaign_audiences_with_cache(campaign_data, audience_cache, update_callback=None):
    """
    Extrae información de audiencias usando un cache de nombres precargado.
    
    Args:
        campaign_data (dict): Datos de la campaña.
        audience_cache (dict): Cache con nombres de audiencias.
        update_callback (callable, optional): Función para actualizar el estado.
    
    Returns:
        str: Información formateada de las audiencias.
    """
    try:
        audiences = campaign_data['data']['attributes'].get('audiences', {})
        
        if not audiences:
            return "N/A"
            
        included = audiences.get('included', [])
        excluded = audiences.get('excluded', [])
        
        result_parts = []
        
        if included:
            # Usar cache para obtener nombres
            included_names = []
            for audience_id in included[:2]:  # Mostrar solo los primeros 2
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
                # Truncar nombres muy largos
                if len(name) > 15:
                    name = name[:12] + "..."
                included_names.append(name)
            
            if len(included) > 2:
                included_names.append(f"+{len(included) - 2}")
            
            result_parts.append(f"Inc: {', '.join(included_names)}")
        
        if excluded:
            excluded_names = []
            for audience_id in excluded[:2]:  # Mostrar solo los primeros 2
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
                # Truncar nombres muy largos
                if len(name) > 15:
                    name = name[:12] + "..."
                excluded_names.append(name)
            
            if len(excluded) > 2:
                excluded_names.append(f"+{len(excluded) - 2}")
            
            result_parts.append(f"Exc: {', '.join(excluded_names)}")
        
        return "; ".join(result_parts) if result_parts else "N/A"
        
    except (KeyError, TypeError) as e:
        if update_callback:
            update_callback(f"Error al obtener audiencias con cache: {str(e)}")
        return "N/A"

# También necesitas agregar esta función auxiliar para optimizar las llamadas
def batch_get_audience_names(audience_ids_list, update_callback=None):
    """
    Obtiene nombres de audiencias en lotes para optimizar las llamadas a la API.
    
    Args:
        audience_ids_list (list): Lista de listas de IDs de audiencias.
        update_callback (callable, optional): Función para actualizar el estado en la UI.
    
    Returns:
        dict: Diccionario con audience_id como clave y nombre como valor.
    """
    # Crear un set único de todos los IDs de audiencias
    all_audience_ids = set()
    for audience_ids in audience_ids_list:
        all_audience_ids.update(audience_ids)
    
    # Cache para almacenar los nombres obtenidos
    audience_names_cache = {}
    
    if update_callback:
        update_callback(f"Obteniendo nombres de {len(all_audience_ids)} audiencias únicas...")
    
    for i, audience_id in enumerate(all_audience_ids):
        try:
            if update_callback and i % 10 == 0:  # Actualizar cada 10 audiencias
                update_callback(f"Procesando audiencia {i+1}/{len(all_audience_ids)}")
            
            # Primero intentar como lista
            url = f"{KLAVIYO_URLS['LISTS']}{audience_id}/"
            response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                name = data['data']['attributes'].get('name', f"List-{audience_id[:8]}")
                audience_names_cache[audience_id] = name
                continue
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                time.sleep(retry_after)
                # Reintentar
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    name = data['data']['attributes'].get('name', f"List-{audience_id[:8]}")
                    audience_names_cache[audience_id] = name
                    continue
            
            # Intentar como segmento
            url = f"{KLAVIYO_URLS['SEGMENTS']}{audience_id}/"
            response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                name = data['data']['attributes'].get('name', f"Segment-{audience_id[:8]}")
                audience_names_cache[audience_id] = name
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                time.sleep(retry_after)
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    name = data['data']['attributes'].get('name', f"Segment-{audience_id[:8]}")
                    audience_names_cache[audience_id] = name
                else:
                    audience_names_cache[audience_id] = f"ID-{audience_id[:8]}"
            else:
                audience_names_cache[audience_id] = f"ID-{audience_id[:8]}"
                
        except Exception as e:
            if update_callback:
                update_callback(f"Error al obtener audiencia {audience_id}: {str(e)}")
            audience_names_cache[audience_id] = f"ID-{audience_id[:8]}"
        
        # Pausa pequeña entre solicitudes
        time.sleep(0.1)
    
    return audience_names_cache

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