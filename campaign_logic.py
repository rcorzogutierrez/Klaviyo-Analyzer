# campaign_logic.py
import requests
from collections import defaultdict
from datetime import datetime, timezone, timedelta  # AGREGADO timedelta
from config import ALLOWED_CODES, COUNTRY_TO_CURRENCY, CURRENCY_SYMBOLS, HEADERS_KLAVIYO, CURRENCIES, KLAVIYO_URLS
from klaviyo_api import get_campaign_metrics, get_campaign_details, preload_campaign_details, query_metric_aggregates_post, get_campaign_message_subject
from exchange_rates import obtener_tasas_de_cambio
from utils import format_number, format_percentage
from collections import defaultdict
import time

def get_campaign_audiences_with_cache(campaign_data, audience_cache, update_callback=None):
    """
    Extrae información de audiencias usando un cache de nombres precargado.
    MODIFICADO: Sin truncamiento para usar con sistema dropdown.
    
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
            # Usar cache para obtener nombres - SIN TRUNCAR
            included_names = []
            for audience_id in included[:2]:  # Mostrar solo los primeros 2 para el resumen
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
                # ELIMINAR EL TRUNCAMIENTO - mostrar nombre completo
                included_names.append(name)
            
            if len(included) > 2:
                included_names.append(f"+{len(included) - 2}")
            
            result_parts.append(f"Inc: {', '.join(included_names)}")
        
        if excluded:
            excluded_names = []
            for audience_id in excluded[:2]:  # Mostrar solo los primeros 2 para el resumen
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
                # ELIMINAR EL TRUNCAMIENTO - mostrar nombre completo
                excluded_names.append(name)
            
            if len(excluded) > 2:
                excluded_names.append(f"+{len(excluded) - 2}")
            
            result_parts.append(f"Exc: {', '.join(excluded_names)}")
        
        return "; ".join(result_parts) if result_parts else "N/A"
        
    except (KeyError, TypeError) as e:
        if update_callback:
            update_callback(f"Error al obtener audiencias con cache: {str(e)}")
        return "N/A"
    
def extract_full_audience_data(campaign_data, audience_cache):
    """Extrae los datos completos de audiencias con nombres completos."""
    try:
        audiences = campaign_data['data']['attributes'].get('audiences', {})
        
        if not audiences:
            return None
            
        included = audiences.get('included', [])
        excluded = audiences.get('excluded', [])
        
        result = {}
        
        if included:
            result['included'] = [audience_cache.get(aud_id, f"ID-{aud_id[:8]}") for aud_id in included]
        
        if excluded:
            result['excluded'] = [audience_cache.get(aud_id, f"ID-{aud_id[:8]}") for aud_id in excluded]
        
        return result if result else None
        
    except (KeyError, TypeError):
        return None    

def preload_campaign_details_with_audiences(campaign_ids, cache, audience_cache, temp_data, update_callback=None, view_manager=None):
    """
    Precarga los detalles de múltiples campañas usando el cache de audiencias.
    MODIFICADO para almacenar datos completos en view_manager.
    """
    count = 0
    total_campaigns = len(campaign_ids)
    
    if update_callback:
        update_callback(f"Procesando detalles de campañas...")
    
    for campaign_id in campaign_ids:
        if campaign_id not in cache:
            count += 1
            if update_callback:
                update_callback(f"ACTUALIZAR:Procesando detalles de campañas ({count}/{total_campaigns})")
            
            try:
                # Usar datos temporales si están disponibles
                if campaign_id in temp_data:
                    campaign_data = temp_data[campaign_id]
                else:
                    # Si no están en temp_data, hacer solicitud
                    url = f"{KLAVIYO_URLS['CAMPAIGN_DETAILS']}{campaign_id}/"
                    response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                    if response.status_code == 200:
                        campaign_data = response.json()
                    elif response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 17))
                        if update_callback:
                            update_callback(f"ACTUALIZAR:Rate limit - esperando {retry_after}s (campaña {count}/{total_campaigns})")
                        time.sleep(retry_after)
                        response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                        if response.status_code == 200:
                            campaign_data = response.json()
                        else:
                            continue
                    else:
                        continue
                
                # Procesar datos de la campaña
                campaign_name = campaign_data['data']['attributes'].get('name', f"Campaign {campaign_id}")
                send_time = campaign_data['data']['attributes'].get('send_time', 'N/A')
                
                if send_time != 'N/A':
                    send_time = datetime.fromisoformat(send_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')

                # Obtener subject line, preview text y template_id
                subject_line, preview_text, template_id = get_campaign_message_subject(campaign_data, None)  # Sin update_callback

                # Obtener audiencias usando el cache
                audiences_info = get_campaign_audiences_with_cache(campaign_data, audience_cache, None)  # Sin update_callback

                # NUEVO: Extraer audiencias completas para el view_manager
                if view_manager:
                    full_audiences = extract_full_audience_data(campaign_data, audience_cache)
                    # Almacenar usando el campaign_id como clave temporal
                    if full_audiences:
                        view_manager.audience_data[f"temp_{campaign_id}"] = full_audiences

                result = (campaign_name, send_time, subject_line, preview_text, template_id, audiences_info)
                cache[campaign_id] = result
                
            except Exception as e:
                if update_callback:
                    update_callback(f"ACTUALIZAR:Error procesando campaña {count}/{total_campaigns}: {str(e)}")
                cache[campaign_id] = (f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A")
    
    if update_callback:
        update_callback(f"ACTUALIZAR:✅ Completado: detalles de {total_campaigns} campañas procesadas")


def obtener_campanas(list_start_date, list_end_date, update_callback, view_manager=None, include_audience_sizes=False):
    """
    Función modificada para incluir Opens únicos calculados y filtrado inteligente de fechas.
    
    Args:
        list_start_date (str): Fecha de inicio
        list_end_date (str): Fecha de fin  
        update_callback (callable): Función para actualizar UI
        view_manager: Manager de vistas para datos de audiencias
        include_audience_sizes (bool): Si True, obtiene los tamaños de audiencias (MÁS LENTO)
    """
    # DEBUG: Mostrar fechas solicitadas
    if update_callback:
        update_callback(f"🔍 DEBUG: Buscando campañas del {list_start_date} al {list_end_date}")
    
    # Obtener el ID de la métrica de conversión
    conversion_metric_id = None
    try:
        response = requests.get("https://a.klaviyo.com/api/metrics/", headers=HEADERS_KLAVIYO, timeout=30)
        response.raise_for_status()
        metrics_data = response.json()
        if 'data' in metrics_data:
            conversion_metric_id = metrics_data['data'][0]['id']
    except requests.exceptions.RequestException as e:
        if update_callback:
            update_callback(f"Error al obtener métricas: {str(e)}")
        return None, f"Error al obtener métricas: {str(e)}"

    if not conversion_metric_id:
        if update_callback:
            update_callback("No se pudo obtener el ID de la métrica de conversión")
        return None, "No se pudo obtener el ID de la métrica de conversión."

    if update_callback:
        update_callback("Obteniendo rango de fechas y detalles de métricas...")
    
    # Intentar con el rango original primero
    metrics = get_campaign_metrics(list_start_date, list_end_date, conversion_metric_id, update_callback)
    
    # Si no hay campañas, extender el rango automáticamente
    extended_search = False
    if not metrics:
        if update_callback:
            update_callback("⚠️ No se encontraron campañas en el rango original. Extendiendo búsqueda a los últimos 7 días...")
        
        # Calcular fecha extendida (7 días antes de la fecha de inicio)
        try:
            start_date_obj = datetime.strptime(list_start_date, "%Y-%m-%d")
            extended_start_date = (start_date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
            
            if update_callback:
                update_callback(f"🔄 Buscando campañas del {extended_start_date} al {list_end_date} (rango extendido)")
            
            metrics = get_campaign_metrics(extended_start_date, list_end_date, conversion_metric_id, update_callback)
            extended_search = True
            
        except Exception as e:
            if update_callback:
                update_callback(f"Error al extender el rango de fechas: {str(e)}")

    if not metrics:
        if update_callback:
            update_callback("No se encontraron campañas incluso con el rango extendido.")
        return None, "No se encontraron campañas en el rango de fechas seleccionado ni en los 7 días anteriores."

    # Informar si se usó rango extendido
    if extended_search and update_callback:
        update_callback(f"✅ Se encontraron {len(metrics)} campañas usando el rango extendido")

    if update_callback:
        update_callback("Obteniendo detalles de las campañas...")
    campaign_ids = [result['groupings']['campaign_id'] for result in metrics]
    campaign_details_cache = {}
    
    # NUEVA SECCIÓN: Preparar cache de audiencias
    if update_callback:
        update_callback("Precargando información de audiencias...")
    
    # Obtener todas las audiencias de todas las campañas primero
    all_audience_ids = []
    temp_campaign_data = {}
    
    # Primera pasada: obtener datos básicos de campañas y extraer IDs de audiencias
    for i, campaign_id in enumerate(campaign_ids):
        if update_callback and i % 10 == 0:
            update_callback(f"ACTUALIZAR:Extrayendo audiencias de campañas ({i+1}/{len(campaign_ids)})")
        
        try:
            url = f"{KLAVIYO_URLS['CAMPAIGN_DETAILS']}{campaign_id}/"
            response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
            if response.status_code == 200:
                campaign_data = response.json()
                temp_campaign_data[campaign_id] = campaign_data
                
                # Extraer IDs de audiencias
                audiences = campaign_data['data']['attributes'].get('audiences', {})
                included = audiences.get('included', [])
                excluded = audiences.get('excluded', [])
                all_audience_ids.extend(included + excluded)
                
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 17))
                if update_callback:
                    update_callback(f"ACTUALIZAR:Rate limit - esperando {retry_after}s (campaña {i+1}/{len(campaign_ids)})")
                time.sleep(retry_after)
                # Reintentar
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                if response.status_code == 200:
                    campaign_data = response.json()
                    temp_campaign_data[campaign_id] = campaign_data
                    audiences = campaign_data['data']['attributes'].get('audiences', {})
                    included = audiences.get('included', [])
                    excluded = audiences.get('excluded', [])
                    all_audience_ids.extend(included + excluded)
        except Exception as e:
            if update_callback:
                update_callback(f"ACTUALIZAR:Error obteniendo campaña {i+1}/{len(campaign_ids)}: {str(e)}")
    
    # Mensaje de finalización para extracción de audiencias
    if update_callback:
        update_callback(f"ACTUALIZAR:✅ Completado: audiencias extraídas de {len(campaign_ids)} campañas")
    
    # Precargar nombres de audiencias únicas CON/SIN TAMAÑOS según el parámetro
    unique_audience_ids = list(set(all_audience_ids))
    audience_names_cache = {}
    
    if unique_audience_ids:
        if include_audience_sizes:
            if update_callback:
                update_callback(f"Obteniendo nombres y tamaños de {len(unique_audience_ids)} audiencias únicas (esto puede tomar varios minutos)...")
        else:
            if update_callback:
                # Mensaje inicial que se va a actualizar
                update_callback(f"Obteniendo nombres de {len(unique_audience_ids)} audiencias únicas...")
        
        for i, audience_id in enumerate(unique_audience_ids):
            # Actualizar la misma línea cada audiencia procesada
            if update_callback:
                update_callback(f"ACTUALIZAR:Procesando audiencia {i+1}/{len(unique_audience_ids)}")
            
            try:
                # VERSIÓN RÁPIDA SIN TAMAÑOS (CÓDIGO ORIGINAL)
                # Intentar como lista primero
                url = f"{KLAVIYO_URLS['LISTS']}{audience_id}/"
                response = requests.get(url, headers=HEADERS_KLAVIYO, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    name = data['data']['attributes'].get('name', f"List-{audience_id[:8]}")
                    audience_names_cache[audience_id] = name
                    continue
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 10))
                    if update_callback:
                        update_callback(f"ACTUALIZAR:Rate limit en audiencias - esperando {retry_after}s (audiencia {i+1}/{len(unique_audience_ids)})")
                    time.sleep(retry_after)
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
                    if update_callback:
                        update_callback(f"ACTUALIZAR:Rate limit en segmentos - esperando {retry_after}s (audiencia {i+1}/{len(unique_audience_ids)})")
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
                    update_callback(f"ACTUALIZAR:Error obteniendo audiencia {i+1}/{len(unique_audience_ids)}: {str(e)}")
                audience_names_cache[audience_id] = f"ID-{audience_id[:8]}"
            
            # Pausa entre solicitudes para evitar rate limiting
            time.sleep(0.1)
        
        # Mensaje final para esta sección
        if update_callback:
            update_callback(f"ACTUALIZAR:✅ Completado: {len(unique_audience_ids)} audiencias procesadas")
    
    # NUEVO: Pasar el cache de nombres al ViewManager
    if view_manager:
        view_manager.set_audience_names_cache(audience_names_cache)
    
    # Ahora precargar detalles de campañas usando el cache de audiencias
    preload_campaign_details_with_audiences(
        campaign_ids, 
        campaign_details_cache, 
        audience_names_cache, 
        temp_campaign_data, 
        update_callback,
        view_manager  # PASAR VIEW_MANAGER
    )

    if update_callback:
        update_callback("Procesando datos de campañas, métricas de órdenes completadas y tasas de cambio...")
    filtered_campaigns = []
    start_dt = datetime.strptime(f"{list_start_date}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_dt = datetime.strptime(f"{list_end_date}T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")

    # Determinar las monedas necesarias basadas en los países de las campañas
    country_codes = set()
    for result in metrics:
        campaign_id = result['groupings']['campaign_id']
        name, _, _, _, _, _ = campaign_details_cache.get(campaign_id, (f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A"))
        partes = name.split("_")
        country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
        country_codes.add(country_code)
    required_currencies = [COUNTRY_TO_CURRENCY.get(code, "USD") for code in country_codes]

    # Obtener tasas de cambio solo para las monedas necesarias
    tasas = obtener_tasas_de_cambio(base="USD", symbols=required_currencies)
    if not tasas:
        if update_callback:
            update_callback("No se pudieron obtener las tasas de cambio. Usando valores originales.")
        tasas = {currency: 1.0 for currency in CURRENCIES}  # Fallback: usar 1.0 si falla la API

    # Obtener métricas de órdenes completadas para todas las campañas
    fecha_inicio = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    fecha_fin_ordenes = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    order_completed_data = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "interval": "day",
                "page_size": 500,
                "timezone": "UTC",
                "measurements": ["unique", "sum_value", "count"],
                "by": ["$attributed_message"],
                "filter": [
                    f"greater-or-equal(datetime,{fecha_inicio})",
                    f"less-than(datetime,{fecha_fin_ordenes})"
                ],
                "metric_id": "QXw4AK"
            }
        }
    }

    order_completed_metrics = defaultdict(lambda: {"unique": 0, "sum_value": 0, "count": 0})
    try:
        response = requests.post(KLAVIYO_URLS["METRIC_AGGREGATES"], json=order_completed_data, headers=HEADERS_KLAVIYO, timeout=30)
        response.raise_for_status()
        data = response.json()["data"]["attributes"]
        measurements_data = data.get("data", [])
        for entry in measurements_data:
            campaign_id = entry["dimensions"][0] if len(entry["dimensions"]) > 0 else "N/A"
            unique = sum(entry.get("measurements", {}).get("unique", []))
            sum_value = sum(entry.get("measurements", {}).get("sum_value", []))
            count = sum(entry.get("measurements", {}).get("count", []))
            order_completed_metrics[campaign_id]["unique"] += unique
            order_completed_metrics[campaign_id]["sum_value"] += sum_value
            order_completed_metrics[campaign_id]["count"] += count
    except requests.exceptions.RequestException as e:
        if update_callback:
            update_callback(f"Error al obtener métricas de órdenes completadas: {str(e)}")

    # DEBUG: Contador de campañas procesadas y filtradas
    total_campaigns_processed = 0
    campaigns_in_range = 0
    campaigns_out_of_range = []
    
    for result in metrics:
        total_campaigns_processed += 1
        campaign_id = result['groupings']['campaign_id']
        name, send_time, subject, preview, template_id, audiences_info = campaign_details_cache.get(
            campaign_id, 
            (f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A")
        )
   
        open_rate = round(result['statistics']['open_rate'] * 100, 2)
        click_rate = round(result['statistics']['click_rate'] * 100, 2)
        delivered = int(result['statistics']['delivered'])
        
        # ===== NUEVO: CALCULAR OPENS ÚNICOS =====
        opens_unicos = int(delivered * (open_rate / 100))
        
        # DEBUG: Mostrar cálculo de opens
        if update_callback and total_campaigns_processed <= 3:  # Mostrar solo las primeras 3 para no saturar
            update_callback(f"📊 DEBUG Campaña '{name[:30]}...': Delivered={delivered}, Open Rate={open_rate}% → Opens únicos={opens_unicos}")

        try:
            send_dt = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S") if send_time != 'N/A' else None
            if send_dt and start_dt <= send_dt <= end_dt:
                campaigns_in_range += 1
                
                # Obtener métricas de órdenes completadas para esta campaña
                order_metrics = order_completed_metrics[campaign_id]
                
                # Determinar la moneda local basada en el país (del nombre de la campaña)
                partes = name.split("_")
                country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
                currency = COUNTRY_TO_CURRENCY.get(country_code, "USD")
                
                # Valor en moneda local (sin conversión)
                local_value = order_metrics["sum_value"]
                
                # Convertir sum_value a dólares (USD) solo si no es una moneda en dólares (pa, sv, vi)
                usd_value = local_value
                if country_code not in {"pa", "sv", "vi"}:  # No convertir si es Panamá, El Salvador, o Islas Vírgenes (USD)
                    usd_rate = tasas.get(currency, 1.0)  # Tasa de cambio a USD, 1.0 si no hay tasa
                    usd_value = local_value / usd_rate if usd_rate != 0 else local_value  # Evitar división por cero
                
                # Calcular "Per Recipient" (Total Value en USD dividido por Recibidos)
                per_recipient = usd_value / delivered if delivered > 0 else 0.0
                
                # DEBUG: Comparación Orders vs Opens
                if update_callback and order_metrics["unique"] > 0:
                    ratio = (order_metrics["unique"] / opens_unicos * 100) if opens_unicos > 0 else 0
                    if ratio > 5:  # Solo mostrar si la tasa de conversión es significativa
                        update_callback(f"💰 Conversión: {name[:30]}... → {order_metrics['unique']} orders / {opens_unicos} opens = {ratio:.1f}%")
                
                filtered_campaigns.append({
                    'campaign_id': campaign_id,
                    'campaign_name': name,
                    'send_time': send_time,
                    'open_rate': open_rate,
                    'click_rate': click_rate,
                    'delivered': delivered,
                    'opens_unicos': opens_unicos,  # NUEVO CAMPO
                    'subject_line': subject,
                    'preview_text': preview,
                    'template_id': template_id,
                    'audiences': audiences_info,
                    'order_unique': order_metrics["unique"],
                    'order_sum_value': usd_value,
                    'order_sum_value_local': local_value,
                    'order_count': order_metrics["count"],
                    'per_recipient': per_recipient,
                })
            else:
                # Campaña fuera del rango
                if send_dt:
                    campaigns_out_of_range.append(f"{name[:30]}... ({send_time})")
                    
        except ValueError as ve:
            if update_callback:
                update_callback(f"Error en formato de send_time para {name}: {send_time} - Error: {ve}")
            return None, f"Formato de send_time inválido para {name}: {send_time}"

    # DEBUG: Resumen final
    if update_callback:
        update_callback(f"📈 DEBUG RESUMEN:")
        update_callback(f"   - Total campañas procesadas: {total_campaigns_processed}")
        update_callback(f"   - Campañas en rango de fechas: {campaigns_in_range}")
        update_callback(f"   - Campañas filtradas (fuera de rango): {len(campaigns_out_of_range)}")
        if campaigns_out_of_range and len(campaigns_out_of_range) <= 5:
            for camp in campaigns_out_of_range[:5]:
                update_callback(f"      ↳ {camp}")
        if extended_search:
            update_callback(f"   ⚠️ Se usó rango extendido de fechas para encontrar campañas")

    if update_callback:
        update_callback(f"ACTUALIZAR:Procesando campañas filtradas: {len(filtered_campaigns)}")
    update_callback(f"ACTUALIZAR:✅ Carga completada - Total: {len(filtered_campaigns)} campañas con Opens únicos calculados")

    # Formatear las campañas para la salida esperada - INCLUIR opens_unicos
    campaigns_list = [
        (idx, camp['campaign_id'], camp['campaign_name'], camp['send_time'], camp['open_rate'], camp['click_rate'], 
         camp['delivered'], camp['opens_unicos'], camp['subject_line'], camp['preview_text'], camp['template_id'],
         camp['audiences'], camp['order_unique'], camp['order_sum_value'], camp['order_sum_value_local'], camp['order_count'], camp['per_recipient'])
        for idx, camp in enumerate(filtered_campaigns, start=1)
    ]
    
    return campaigns_list, None

def agrupar_por_pais(campanas):
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, *_ = camp  # Usar *_ para manejar campos adicionales
        partes = name.split("_")
        pais = partes[-1].strip().lower() if len(partes) > 1 else "desconocido"
        grupos[pais].append(camp)
    return grupos

def agrupar_por_fecha(campanas):
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, *_ = camp  # Usar *_ para manejar campos adicionales
        try:
            date_only = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            date_only = send_time
        grupos[date_only].append(camp)
    return grupos

def agrupar_por_fecha_y_prefijo(campanas):
    """Agrupa campañas por fecha, y dentro de cada fecha, por prefijo (ecom, cross, etc)."""
    grupos = defaultdict(lambda: defaultdict(list))
    for camp in campanas:
        _, _, name, send_time, *_ = camp  # Usar *_ para manejar cualquier número de campos adicionales
        try:
            fecha = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            fecha = send_time

        prefijo = name.split("_")[0].lower() if "_" in name else "otro"
        grupos[fecha][prefijo].append(camp)
    return grupos

def add_campaign_row(camp, show_local_value=True, view_manager=None):
    """Función auxiliar para crear una fila de campaña con indicadores de expansión y Opens únicos."""
    # MODIFICADO: Ahora incluye opens_unicos (índice 7)
    idx, campaign_id, name, send_time, open_rate, click_rate, delivered, opens_unicos, subject, preview, template_id, audiences, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
    
    partes = name.split("_")
    country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
    currency = COUNTRY_TO_CURRENCY.get(country_code, "USD")
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")

    # MODIFICAR LA PRIMERA COLUMNA PARA INCLUIR INDICADOR DE EXPANSIÓN
    if audiences != "N/A" and audiences:
        numero_display = f"▶ {idx}"  # Mostrar indicador si hay audiencias
    else:
        numero_display = str(idx)  # Sin indicador si no hay audiencias

    values = [
        numero_display,  # Primera columna modificada
        name,
        send_time,
        format_percentage(open_rate),
        format_percentage(click_rate),
        format_number(delivered),
        format_number(opens_unicos),  # NUEVO: Opens únicos
        format_number(int(order_unique)),
        format_number(order_sum_value, is_currency=True),
    ]
    
    if show_local_value:
        values.append(format_number(order_sum_value_local, is_currency=True, currency_symbol=currency_symbol))
    else:
        values.append("")
    
    values.extend([
        format_number(per_recipient, is_currency=True),
        format_number(int(order_count)),
        # ELIMINAR LA COLUMNA DE AUDIENCIAS - solo Subject y Preview
        subject,
        preview,
    ])
    
    return values, audiences


def mostrar_campanas_en_tabla(campanas, tree, grouping="País", show_local_value=True, template_ids_dict=None, view_manager=None):
    """Función principal modificada para incluir Opens únicos en la tabla y actualizar grand_total_tabla."""
    tree.delete(*tree.get_children())

    # MODIFICADO: Agregar columna "OpensUnicos" después de "Recibios"
    columns = ("Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OpensUnicos", "OrderUnique",
               "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "Subject", "Preview")
    tree["columns"] = columns

    # Limpiar los datos de audiencias anteriores si hay view_manager
    if view_manager:
        view_manager.audience_data.clear()
        view_manager.expanded_rows.clear()

    # CONFIGURAR ENCABEZADOS CON NUEVA COLUMNA
    for col, text in zip(columns, ("# / Audiencias", "Nombre", "Fecha de Envío", "Open Rate", "Click Rate", "Recibidos", "Opens Únicos",
                                   "Unique Orders", "Total Value (USD)", "Total Value (Local)", "Per Recipient", "Order Count", "Subject Line", "Preview Text")):
        tree.heading(col, text=text)

    # Configurar anchos de columnas (CON la nueva columna Opens Únicos)
    tree.column("Numero", width=80, anchor="center")  # Aumentado para mostrar "▶ #"
    tree.column("Nombre", width=120)
    tree.column("FechaEnvio", width=100)
    tree.column("OpenRate", width=80, anchor="center")
    tree.column("ClickRate", width=80, anchor="center")
    tree.column("Recibios", width=100, anchor="center")
    tree.column("OpensUnicos", width=100, anchor="center")  # NUEVA COLUMNA
    tree.column("OrderUnique", width=80, anchor="center")
    tree.column("OrderSumValue", width=120, anchor="e")
    tree.column("OrderSumValueLocal", width=120 if show_local_value else 0, anchor="e", stretch=show_local_value)
    tree.column("PerRecipient", width=120, anchor="e")
    tree.column("OrderCount", width=80, anchor="center")
    tree.column("Subject", width=180)
    tree.column("Preview", width=180)

    def process_campaign_for_table(camp, show_local_value=True):
        """Procesa una campaña para mostrarla en la tabla."""
        values, audiences = add_campaign_row(camp, show_local_value, view_manager)
        idx = camp[0]
        campaign_id = camp[1]
        template_id = camp[10]  # AJUSTADO: template_id está en índice 10 ahora
        
        item_id = tree.insert("", "end", values=values, tags=(f"campaign_{campaign_id}", "campaign_row"))
        
        # Almacenar template_id si se proporciona el diccionario
        if template_ids_dict is not None and template_id is not None:
            template_ids_dict[item_id] = template_id
        
        # ALMACENAR DATOS DE AUDIENCIAS EN VIEW_MANAGER
        if view_manager and audiences != "N/A":
            view_manager.store_audience_data(item_id, audiences)
        
        return item_id

    def calculate_subtotals(camps, show_local_value=True):
        total_delivered = 0
        total_opens_unicos = 0  # NUEVO
        weighted_open = 0
        weighted_click = 0
        total_weight = 0
        total_unique = 0
        total_sum_value = 0
        total_sum_value_local = 0
        total_count = 0
        total_per_recipient_weighted = 0
        total_delivered_for_weight = 0

        for camp in camps:
            # AJUSTADO: opens_unicos está en índice 7
            _, _, _, _, open_rate, click_rate, delivered, opens_unicos, _, _, _, _, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
            total_delivered += delivered
            total_opens_unicos += opens_unicos  # NUEVO
            weighted_open += (open_rate * delivered) / 100
            weighted_click += (click_rate * delivered) / 100
            total_weight += delivered
            total_unique += order_unique
            total_sum_value += order_sum_value
            total_sum_value_local += order_sum_value_local
            total_count += order_count
            total_per_recipient_weighted += per_recipient * delivered
            total_delivered_for_weight += delivered

        if total_weight > 0:
            avg_open_rate = round((weighted_open / total_weight) * 100, 2)
            avg_click_rate = round((weighted_click / total_weight) * 100, 2)
            per_recipient_weighted_avg = total_per_recipient_weighted / total_delivered_for_weight if total_delivered_for_weight > 0 else 0.0
            values = [
                "",
                "Subtotal",
                "",
                format_percentage(avg_open_rate),
                format_percentage(avg_click_rate),
                format_number(total_delivered),
                format_number(total_opens_unicos),  # NUEVO
                format_number(int(total_unique)),
                format_number(total_sum_value, is_currency=True),
            ]
            if show_local_value:
                values.append(format_number(total_sum_value_local, is_currency=True))
            else:
                values.append("")
            values.append(format_number(per_recipient_weighted_avg, is_currency=True))
            values.extend([
                format_number(int(total_count)),
                "",  # Subject
                "",  # Preview
            ])
            return values, {
                "delivered": total_delivered,
                "opens_unicos": total_opens_unicos,  # NUEVO - ASEGURAR QUE ESTÉ AQUÍ
                "weighted_open": weighted_open,
                "weighted_click": weighted_click,
                "total_weight": total_weight,
                "unique": total_unique,
                "sum_value": total_sum_value,
                "sum_value_local": total_sum_value_local,  # AGREGADO para consistencia
                "count": total_count,
                "per_recipient_weighted": total_per_recipient_weighted,
                "delivered_for_weight": total_delivered_for_weight
            }
        return None, None

    all_subtotals = []

    if grouping == "País":
        grupos = agrupar_por_pais(campanas)
        for pais in sorted(grupos.keys()):
            tree.insert("", "end", values=(f"{pais.upper()}", "", "", "", "", "", "", "", "", "", "", "", "", ""), tags=("bold",))
            for camp in sorted(grupos[pais], key=lambda x: x[0]):
                process_campaign_for_table(camp, show_local_value)

            subtotal_values, subtotal_data = calculate_subtotals(grupos[pais], show_local_value)
            if subtotal_values:
                tree.insert("", "end", values=subtotal_values, tags=("bold",))
                all_subtotals.append(subtotal_data)
            tree.insert("", "end", values=("",) * 14)  # 14 columnas (con Opens Únicos)
    else:
        grupos_fecha = defaultdict(lambda: defaultdict(list))
        for camp in campanas:
            _, _, name, send_time, *_ = camp
            try:
                fecha = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            except ValueError:
                fecha = send_time
            prefijo = name.split("_")[0].lower() if "_" in name else "otro"
            grupos_fecha[fecha][prefijo].append(camp)

        for fecha in sorted(grupos_fecha.keys()):
            tree.insert("", "end", values=(fecha, "", "", "", "", "", "", "", "", "", "", "", "", ""), tags=("bold",))
            for prefijo in sorted(grupos_fecha[fecha].keys()):               
                tree.insert("", "end", values=(prefijo, "", "", "", "", "", "", "", "", "", "", "", "", ""), tags=("bold",))

                for camp in sorted(grupos_fecha[fecha][prefijo], key=lambda x: x[0]):
                    process_campaign_for_table(camp, show_local_value)  # CAMBIADO: usar show_local_value del parámetro

                subtotal_values, subtotal_data = calculate_subtotals(grupos_fecha[fecha][prefijo], show_local_value)  # CAMBIADO: usar show_local_value del parámetro
                if subtotal_values:
                    tree.insert("", "end", values=subtotal_values, tags=("bold",))
                    all_subtotals.append(subtotal_data)
                tree.insert("", "end", values=("",) * 14)  # 14 columnas (con Opens Únicos)

    # ========== ACTUALIZACIÓN CRÍTICA DE grand_total_tabla ==========
    print(f"\n========== DEBUG GRAND TOTAL ==========")
    print(f"Subtotales disponibles: {len(all_subtotals)}")
    print(f"view_manager existe: {view_manager is not None}")
    
    if view_manager and hasattr(view_manager, 'grand_total_tabla') and view_manager.grand_total_tabla:
        print(f"grand_total_tabla existe: True")
        
        # DEBUG: Inspeccionar la configuración de columnas
        print(f"Columnas configuradas: {view_manager.grand_total_tabla['columns']}")
        print(f"Número de columnas: {len(view_manager.grand_total_tabla['columns'])}")
        
        # Verificar el ancho de cada columna
        for col in view_manager.grand_total_tabla['columns']:
            col_config = view_manager.grand_total_tabla.column(col)
            print(f"Columna '{col}': width={col_config['width']}, stretch={col_config['stretch']}")
        
        if all_subtotals and len(all_subtotals) > 0:
            # Calcular totales generales
            grand_total_delivered = sum(s.get("delivered", 0) for s in all_subtotals)
            grand_total_opens_unicos = sum(s.get("opens_unicos", 0) for s in all_subtotals)
            grand_total_weighted_open = sum(s.get("weighted_open", 0) for s in all_subtotals)
            grand_total_weighted_click = sum(s.get("weighted_click", 0) for s in all_subtotals)
            grand_total_weight = sum(s.get("total_weight", 0) for s in all_subtotals)
            grand_total_unique = sum(s.get("unique", 0) for s in all_subtotals)
            grand_total_sum_value = sum(s.get("sum_value", 0) for s in all_subtotals)
            grand_total_count = sum(s.get("count", 0) for s in all_subtotals)
            grand_total_per_recipient_weighted = sum(s.get("per_recipient_weighted", 0) for s in all_subtotals)
            grand_total_delivered_for_weight = sum(s.get("delivered_for_weight", 0) for s in all_subtotals)
            
            print(f"Opens únicos total calculado: {grand_total_opens_unicos}")
            print(f"Delivered total: {grand_total_delivered}")
            print(f"Opens por subtotal: {[s.get('opens_unicos', 0) for s in all_subtotals]}")
            
            if grand_total_weight > 0:
                grand_avg_open_rate = round((grand_total_weighted_open / grand_total_weight) * 100, 2)
                grand_avg_click_rate = round((grand_total_weighted_click / grand_total_weight) * 100, 2)
                grand_per_recipient_avg = grand_total_per_recipient_weighted / grand_total_delivered_for_weight if grand_total_delivered_for_weight > 0 else 0.0
                
                # Limpiar la tabla grand_total_tabla
                view_manager.grand_total_tabla.delete(*view_manager.grand_total_tabla.get_children())
                
                # Formatear el valor de opens únicos
                opens_formatted = format_number(grand_total_opens_unicos)
                print(f"Opens únicos formateado: {opens_formatted}")
                
                # INSERTAR valores en el orden exacto que espera grand_total_tabla
                valores_grand_total = (
                    "",  # Numero
                    "Total General",  # Nombre
                    format_percentage(grand_avg_open_rate),  # OpenRate
                    format_percentage(grand_avg_click_rate),  # ClickRate
                    format_number(grand_total_delivered),  # Recibidos
                    format_number(int(grand_total_unique)),  # OrderUnique
                    format_number(grand_total_sum_value, is_currency=True),  # OrderSumValue
                    format_number(grand_per_recipient_avg, is_currency=True),  # PerRecipient
                    format_number(int(grand_total_count)),  # OrderCount
                    opens_formatted  # OpenUnique - POSICIÓN 9
                )
                
                print(f"Valores a insertar: {valores_grand_total}")
                print(f"Valor en posición 9 (OpenUnique): {valores_grand_total[9]}")
                
                # Insertar en la tabla
                inserted_item = view_manager.grand_total_tabla.insert("", "end", values=valores_grand_total, tags=("grand_total",))
                
                # RECONFIGURAR las columnas para ajuste dinámico pero manteniendo OpenUnique visible
                try:
                    # Obtener el ancho total disponible (aproximado)
                    # Configurar las columnas con stretch para que se ajusten dinámicamente
                    view_manager.grand_total_tabla.column("Numero", width=0, stretch=False)  # Ocultar
                    view_manager.grand_total_tabla.column("Nombre", width=150, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("OpenRate", width=80, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("ClickRate", width=80, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("Recibios", width=100, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("OrderUnique", width=100, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("OrderSumValue", width=120, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("PerRecipient", width=100, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("OrderCount", width=100, stretch=True)  # Expandible
                    view_manager.grand_total_tabla.column("OpenUnique", width=100, minwidth=80, stretch=True)  # CRÍTICO: expandible pero con ancho mínimo
                    
                    # Asegurar que los encabezados sean correctos
                    view_manager.grand_total_tabla.heading("OpenUnique", text="Open Únicos")
                    
                    print(f"Columnas reconfiguradas con stretch=True para ajuste dinámico")
                        
                except Exception as e:
                    print(f"Error reconfigurando columnas: {e}")
                
                # Forzar actualización completa
                view_manager.grand_total_tabla.update_idletasks()
                view_manager.grand_total_tabla.update()
                
                # Verificar inserción
                if inserted_item:
                    valores_insertados = view_manager.grand_total_tabla.item(inserted_item, 'values')
                    print(f"Valores realmente insertados: {valores_insertados}")
                    
                    # Intentar diferentes métodos para establecer el valor
                    try:
                        # Método 1: set directo con nombre de columna
                        view_manager.grand_total_tabla.set(inserted_item, "OpenUnique", opens_formatted)
                        print(f"Método 1: Valor forzado en columna OpenUnique: {opens_formatted}")
                    except Exception as e:
                        print(f"Método 1 falló: {e}")
                    
                    try:
                        # Método 2: set con índice de columna
                        view_manager.grand_total_tabla.set(inserted_item, "#10", opens_formatted)
                        print(f"Método 2: Valor forzado en columna #10: {opens_formatted}")
                    except Exception as e:
                        print(f"Método 2 falló: {e}")
                    
                    # NUEVO: Programar actualización retrasada para sobrescribir cualquier cambio posterior
                    def update_opens_delayed():
                        try:
                            # Obtener el item actual (por si fue recreado)
                            items = view_manager.grand_total_tabla.get_children()
                            if items:
                                item = items[0]  # Debería ser el único item
                                # Obtener valores actuales
                                current_values = list(view_manager.grand_total_tabla.item(item, 'values'))
                                print(f"DEBUG DELAYED: Valores actuales antes de actualizar: {current_values}")
                                
                                # Actualizar solo la columna 9 (OpenUnique)
                                current_values[9] = opens_formatted
                                
                                # Establecer todos los valores de nuevo
                                view_manager.grand_total_tabla.item(item, values=current_values)
                                
                                # También intentar con set
                                view_manager.grand_total_tabla.set(item, "OpenUnique", opens_formatted)
                                
                                print(f"DEBUG DELAYED: Opens únicos actualizado a {opens_formatted}")
                                
                                # Verificar que se actualizó
                                final_values = view_manager.grand_total_tabla.item(item, 'values')
                                print(f"DEBUG DELAYED: Valores finales: {final_values}")
                                
                        except Exception as e:
                            print(f"DEBUG DELAYED: Error actualizando: {e}")
                    
                    # Programar la actualización para 100ms después
                    if hasattr(view_manager.grand_total_tabla, 'after'):
                        view_manager.grand_total_tabla.after(100, update_opens_delayed)
                        print("Actualización retrasada programada para 100ms")
                    
                    # Verificar valor final en cada columna
                    print("\nValores finales por columna:")
                    for i, col in enumerate(view_manager.grand_total_tabla['columns']):
                        try:
                            val = view_manager.grand_total_tabla.set(inserted_item, col)
                            print(f"  Columna {i} ('{col}'): '{val}'")
                        except:
                            print(f"  Columna {i} ('{col}'): ERROR al leer")
                    
                    # Forzar actualización visual
                    view_manager.grand_total_tabla.update_idletasks()
                    view_manager.grand_total_tabla.update()
                    
            else:
                print(f"No se actualiza porque grand_total_weight = {grand_total_weight}")
        else:
            print(f"No hay subtotales para procesar")
    else:
        print(f"grand_total_tabla no existe o view_manager no está disponible")
    
    print(f"========================================\n")

    return all_subtotals

def seleccionar_campanas(campanas, input_str):
    seleccionados = []
    vistos = set()
    
    tokens = [t.strip().lower() for t in input_str.split(",") if t.strip()]
    indices = [int(token) - 1 for token in tokens if token.isdigit()]
    
    for token in tokens:
        if len(token) == 2 and token in ALLOWED_CODES:
            for camp in campanas:
                idx, cid, name, send_time, *_ = camp  # Usar *_ para manejar campos adicionales
                partes = name.split("_")
                if len(partes) > 1 and partes[-1].strip().lower() == token:
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
        elif not token.isdigit():
            for camp in campanas:
                idx, cid, name, send_time, *_ = camp  # Usar *_ para manejar campos adicionales
                partes = name.split("_")
                if partes and token in partes[0].lower():
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
    
    for idx in indices:
        if 0 <= idx < len(campanas):
            camp = campanas[idx]
            idx, cid, name, send_time, *_ = camp  # Usar *_ para manejar campos adicionales
            key = (cid, send_time)
            if key not in vistos:
                vistos.add(key)
                seleccionados.append(camp)
    
    return sorted(seleccionados, key=lambda x: x[0])