# campaign_logic.py
import requests
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from config import ALLOWED_CODES, COUNTRY_TO_CURRENCY, CURRENCY_SYMBOLS, HEADERS_KLAVIYO, CURRENCIES, KLAVIYO_URLS
from klaviyo_api import get_campaign_metrics, get_campaign_details, preload_campaign_details, query_metric_aggregates_post, get_campaign_message_subject
from exchange_rates import obtener_tasas_de_cambio
from utils import format_number, format_percentage
import time

def get_campaign_audiences_with_cache(campaign_data, audience_cache, update_callback=None):
    """
    Extrae información de audiencias usando un cache de nombres precargado.
    """
    try:
        audiences = campaign_data['data']['attributes'].get('audiences', {})
        
        if not audiences:
            return "N/A"
            
        included = audiences.get('included', [])
        excluded = audiences.get('excluded', [])
        
        result_parts = []
        
        if included:
            included_names = []
            for audience_id in included[:2]:
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
                included_names.append(name)
            
            if len(included) > 2:
                included_names.append(f"+{len(included) - 2}")
            
            result_parts.append(f"Inc: {', '.join(included_names)}")
        
        if excluded:
            excluded_names = []
            for audience_id in excluded[:2]:
                name = audience_cache.get(audience_id, f"ID-{audience_id[:8]}")
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
                if campaign_id in temp_data:
                    campaign_data = temp_data[campaign_id]
                else:
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
                
                campaign_name = campaign_data['data']['attributes'].get('name', f"Campaign {campaign_id}")
                send_time = campaign_data['data']['attributes'].get('send_time', 'N/A')
                
                if send_time != 'N/A':
                    send_time = datetime.fromisoformat(send_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')

                subject_line, preview_text, template_id = get_campaign_message_subject(campaign_data, None)
                audiences_info = get_campaign_audiences_with_cache(campaign_data, audience_cache, None)

                if view_manager:
                    full_audiences = extract_full_audience_data(campaign_data, audience_cache)
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
    Obtiene y procesa las campañas en el rango de fechas especificado.
    Incluye cálculo de Opens únicos y manejo inteligente de fechas.
    """
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

    if extended_search and update_callback:
        update_callback(f"✅ Se encontraron {len(metrics)} campañas usando el rango extendido")

    if update_callback:
        update_callback("Obteniendo detalles de las campañas...")
    
    campaign_ids = [result['groupings']['campaign_id'] for result in metrics]
    campaign_details_cache = {}
    
    # Preparar cache de audiencias
    if update_callback:
        update_callback("Precargando información de audiencias...")
    
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
                
                audiences = campaign_data['data']['attributes'].get('audiences', {})
                included = audiences.get('included', [])
                excluded = audiences.get('excluded', [])
                all_audience_ids.extend(included + excluded)
                
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 17))
                if update_callback:
                    update_callback(f"ACTUALIZAR:Rate limit - esperando {retry_after}s (campaña {i+1}/{len(campaign_ids)})")
                time.sleep(retry_after)
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
    
    if update_callback:
        update_callback(f"ACTUALIZAR:✅ Completado: audiencias extraídas de {len(campaign_ids)} campañas")
    
    # Precargar nombres de audiencias únicas
    unique_audience_ids = list(set(all_audience_ids))
    audience_names_cache = {}
    
    if unique_audience_ids:
        if update_callback:
            update_callback(f"Obteniendo nombres de {len(unique_audience_ids)} audiencias únicas...")
        
        for i, audience_id in enumerate(unique_audience_ids):
            if update_callback:
                update_callback(f"ACTUALIZAR:Procesando audiencia {i+1}/{len(unique_audience_ids)}")
            
            try:
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
            
            time.sleep(0.1)  # Pausa para evitar rate limiting
        
        if update_callback:
            update_callback(f"ACTUALIZAR:✅ Completado: {len(unique_audience_ids)} audiencias procesadas")
    
    if view_manager:
        view_manager.set_audience_names_cache(audience_names_cache)
    
    # Precargar detalles de campañas
    preload_campaign_details_with_audiences(
        campaign_ids, 
        campaign_details_cache, 
        audience_names_cache, 
        temp_campaign_data, 
        update_callback,
        view_manager
    )

    if update_callback:
        update_callback("Procesando datos de campañas, métricas de órdenes completadas y tasas de cambio...")
    
    filtered_campaigns = []
    start_dt = datetime.strptime(f"{list_start_date}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_dt = datetime.strptime(f"{list_end_date}T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")

    # Determinar las monedas necesarias
    country_codes = set()
    for result in metrics:
        campaign_id = result['groupings']['campaign_id']
        name, _, _, _, _, _ = campaign_details_cache.get(campaign_id, (f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A"))
        partes = name.split("_")
        country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
        country_codes.add(country_code)
    required_currencies = [COUNTRY_TO_CURRENCY.get(code, "USD") for code in country_codes]

    # Obtener tasas de cambio
    tasas = obtener_tasas_de_cambio(base="USD", symbols=required_currencies)
    if not tasas:
        if update_callback:
            update_callback("No se pudieron obtener las tasas de cambio. Usando valores originales.")
        tasas = {currency: 1.0 for currency in CURRENCIES}

    # Obtener métricas de órdenes completadas
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

    # Procesar campañas
    for result in metrics:
        campaign_id = result['groupings']['campaign_id']
        name, send_time, subject, preview, template_id, audiences_info = campaign_details_cache.get(
            campaign_id, 
            (f"Campaign {campaign_id}", 'N/A', "No Subject Line", "No Preview Text", None, "N/A")
        )
   
        open_rate = round(result['statistics']['open_rate'] * 100, 2)
        click_rate = round(result['statistics']['click_rate'] * 100, 2)
        delivered = int(result['statistics']['delivered'])
        
        # Calcular Opens únicos
        opens_unicos = int(delivered * (open_rate / 100))

        try:
            send_dt = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S") if send_time != 'N/A' else None
            if send_dt and start_dt <= send_dt <= end_dt:
                order_metrics = order_completed_metrics[campaign_id]
                
                partes = name.split("_")
                country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
                currency = COUNTRY_TO_CURRENCY.get(country_code, "USD")
                
                local_value = order_metrics["sum_value"]
                
                # Convertir a USD si es necesario
                usd_value = local_value
                if country_code not in {"pa", "sv", "vi"}:
                    usd_rate = tasas.get(currency, 1.0)
                    usd_value = local_value / usd_rate if usd_rate != 0 else local_value
                
                per_recipient = usd_value / delivered if delivered > 0 else 0.0
                
                filtered_campaigns.append({
                    'campaign_id': campaign_id,
                    'campaign_name': name,
                    'send_time': send_time,
                    'open_rate': open_rate,
                    'click_rate': click_rate,
                    'delivered': delivered,
                    'opens_unicos': opens_unicos,
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
                    
        except ValueError as ve:
            if update_callback:
                update_callback(f"Error en formato de send_time para {name}: {send_time} - Error: {ve}")
            return None, f"Formato de send_time inválido para {name}: {send_time}"

    if update_callback:
        update_callback(f"ACTUALIZAR:✅ Carga completada - Total: {len(filtered_campaigns)} campañas")

    # Formatear las campañas para la salida
    campaigns_list = [
        (idx, camp['campaign_id'], camp['campaign_name'], camp['send_time'], camp['open_rate'], camp['click_rate'], 
         camp['delivered'], camp['opens_unicos'], camp['subject_line'], camp['preview_text'], camp['template_id'],
         camp['audiences'], camp['order_unique'], camp['order_sum_value'], camp['order_sum_value_local'], camp['order_count'], camp['per_recipient'])
        for idx, camp in enumerate(filtered_campaigns, start=1)
    ]
    
    return campaigns_list, None

def agrupar_por_pais(campanas):
    """Agrupa campañas por país basándose en el sufijo del nombre."""
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, *_ = camp
        partes = name.split("_")
        pais = partes[-1].strip().lower() if len(partes) > 1 else "desconocido"
        grupos[pais].append(camp)
    return grupos

def agrupar_por_fecha(campanas):
    """Agrupa campañas por fecha de envío."""
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, *_ = camp
        try:
            date_only = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            date_only = send_time
        grupos[date_only].append(camp)
    return grupos

def agrupar_por_fecha_y_prefijo(campanas):
    """Agrupa campañas por fecha y prefijo del nombre."""
    grupos = defaultdict(lambda: defaultdict(list))
    for camp in campanas:
        _, _, name, send_time, *_ = camp
        try:
            fecha = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            fecha = send_time

        prefijo = name.split("_")[0].lower() if "_" in name else "otro"
        grupos[fecha][prefijo].append(camp)
    return grupos

def add_campaign_row(camp, show_local_value=True, view_manager=None):
    """Prepara una fila de campaña para mostrar en la tabla."""
    idx, campaign_id, name, send_time, open_rate, click_rate, delivered, opens_unicos, subject, preview, template_id, audiences, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
    
    partes = name.split("_")
    country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
    currency = COUNTRY_TO_CURRENCY.get(country_code, "USD")
    currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")

    numero_display = f"▶ {idx}" if audiences != "N/A" and audiences else str(idx)

    values = [
        numero_display,
        name,
        send_time,
        format_percentage(open_rate),
        format_percentage(click_rate),
        format_number(delivered),
        format_number(opens_unicos),
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
        subject,
        preview,
    ])
    
    return values, audiences

def mostrar_campanas_en_tabla(campanas, tree, grouping="País", show_local_value=True, template_ids_dict=None, view_manager=None):
    """
    Muestra las campañas en la tabla principal y actualiza el gran total.
    """
    tree.delete(*tree.get_children())

    columns = ("Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OpensUnicos", "OrderUnique",
               "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "Subject", "Preview")
    tree["columns"] = columns

    if view_manager:
        view_manager.audience_data.clear()
        view_manager.expanded_rows.clear()

    # Configurar encabezados
    for col, text in zip(columns, ("# / Audiencias", "Nombre", "Fecha de Envío", "Open Rate", "Click Rate", "Recibidos", "Opens Únicos",
                                   "Unique Orders", "Total Value (USD)", "Total Value (Local)", "Per Recipient", "Order Count", "Subject Line", "Preview Text")):
        tree.heading(col, text=text)

    # Configurar anchos de columnas
    tree.column("Numero", width=80, anchor="center")
    tree.column("Nombre", width=120)
    tree.column("FechaEnvio", width=100)
    tree.column("OpenRate", width=80, anchor="center")
    tree.column("ClickRate", width=80, anchor="center")
    tree.column("Recibios", width=100, anchor="center")
    tree.column("OpensUnicos", width=100, anchor="center")
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
        template_id = camp[10]
        
        item_id = tree.insert("", "end", values=values, tags=(f"campaign_{campaign_id}", "campaign_row"))
        
        if template_ids_dict is not None and template_id is not None:
            template_ids_dict[item_id] = template_id
        
        if view_manager and audiences != "N/A":
            view_manager.store_audience_data(item_id, audiences)
        
        return item_id

    def calculate_subtotals(camps, show_local_value=True):
        """Calcula subtotales para un grupo de campañas."""
        total_delivered = 0
        total_opens_unicos = 0
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
            _, _, _, _, open_rate, click_rate, delivered, opens_unicos, _, _, _, _, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
            total_delivered += delivered
            total_opens_unicos += opens_unicos
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
                format_number(total_opens_unicos),
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
                "",
                "",
            ])
            return values, {
                "delivered": total_delivered,
                "opens_unicos": total_opens_unicos,
                "weighted_open": weighted_open,
                "weighted_click": weighted_click,
                "total_weight": total_weight,
                "unique": total_unique,
                "sum_value": total_sum_value,
                "sum_value_local": total_sum_value_local,
                "count": total_count,
                "per_recipient_weighted": total_per_recipient_weighted,
                "delivered_for_weight": total_delivered_for_weight
            }
        return None, None

    all_subtotals = []

    # Agrupar y mostrar campañas según el tipo de agrupación
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
            tree.insert("", "end", values=("",) * 14)
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
                    process_campaign_for_table(camp, show_local_value)

                subtotal_values, subtotal_data = calculate_subtotals(grupos_fecha[fecha][prefijo], show_local_value)
                if subtotal_values:
                    tree.insert("", "end", values=subtotal_values, tags=("bold",))
                    all_subtotals.append(subtotal_data)
                tree.insert("", "end", values=("",) * 14)

    # Actualizar tabla de gran total si existe
    if view_manager and hasattr(view_manager, 'grand_total_tabla') and view_manager.grand_total_tabla and all_subtotals:
        _update_grand_total_table(view_manager, all_subtotals)

    return all_subtotals

def _update_grand_total_table(view_manager, all_subtotals):
    """
    Función auxiliar para actualizar la tabla de gran total.
    Separada para mejor organización del código.
    """
    # Calcular totales generales
    grand_total = {
        'delivered': sum(s.get("delivered", 0) for s in all_subtotals),
        'opens_unicos': sum(s.get("opens_unicos", 0) for s in all_subtotals),
        'weighted_open': sum(s.get("weighted_open", 0) for s in all_subtotals),
        'weighted_click': sum(s.get("weighted_click", 0) for s in all_subtotals),
        'total_weight': sum(s.get("total_weight", 0) for s in all_subtotals),
        'unique': sum(s.get("unique", 0) for s in all_subtotals),
        'sum_value': sum(s.get("sum_value", 0) for s in all_subtotals),
        'count': sum(s.get("count", 0) for s in all_subtotals),
        'per_recipient_weighted': sum(s.get("per_recipient_weighted", 0) for s in all_subtotals),
        'delivered_for_weight': sum(s.get("delivered_for_weight", 0) for s in all_subtotals)
    }
    
    if grand_total['total_weight'] > 0:
        grand_avg_open_rate = round((grand_total['weighted_open'] / grand_total['total_weight']) * 100, 2)
        grand_avg_click_rate = round((grand_total['weighted_click'] / grand_total['total_weight']) * 100, 2)
        grand_per_recipient_avg = grand_total['per_recipient_weighted'] / grand_total['delivered_for_weight'] if grand_total['delivered_for_weight'] > 0 else 0.0
        
        # Limpiar la tabla
        view_manager.grand_total_tabla.delete(*view_manager.grand_total_tabla.get_children())
        
        # Formatear valores
        opens_formatted = format_number(grand_total['opens_unicos'])
        
        # Insertar valores
        valores_grand_total = (
            "",
            "Total General",
            format_percentage(grand_avg_open_rate),
            format_percentage(grand_avg_click_rate),
            format_number(grand_total['delivered']),
            format_number(int(grand_total['unique'])),
            format_number(grand_total['sum_value'], is_currency=True),
            format_number(grand_per_recipient_avg, is_currency=True),
            format_number(int(grand_total['count'])),
            opens_formatted
        )
        
        inserted_item = view_manager.grand_total_tabla.insert("", "end", values=valores_grand_total, tags=("grand_total",))
        
        # Configurar columnas para ajuste dinámico
        try:
            view_manager.grand_total_tabla.column("Numero", width=0, stretch=False)
            view_manager.grand_total_tabla.column("Nombre", width=150, stretch=True)
            view_manager.grand_total_tabla.column("OpenRate", width=80, stretch=True)
            view_manager.grand_total_tabla.column("ClickRate", width=80, stretch=True)
            view_manager.grand_total_tabla.column("Recibios", width=100, stretch=True)
            view_manager.grand_total_tabla.column("OrderUnique", width=100, stretch=True)
            view_manager.grand_total_tabla.column("OrderSumValue", width=120, stretch=True)
            view_manager.grand_total_tabla.column("PerRecipient", width=100, stretch=True)
            view_manager.grand_total_tabla.column("OrderCount", width=100, stretch=True)
            view_manager.grand_total_tabla.column("OpenUnique", width=100, minwidth=80, stretch=True)
            
            view_manager.grand_total_tabla.heading("OpenUnique", text="Open Únicos")
        except Exception:
            pass
        
        # Actualización retrasada para asegurar persistencia del valor
        def update_opens_delayed():
            try:
                items = view_manager.grand_total_tabla.get_children()
                if items:
                    item = items[0]
                    current_values = list(view_manager.grand_total_tabla.item(item, 'values'))
                    current_values[9] = opens_formatted
                    view_manager.grand_total_tabla.item(item, values=current_values)
                    view_manager.grand_total_tabla.set(item, "OpenUnique", opens_formatted)
            except Exception:
                pass
        
        if hasattr(view_manager.grand_total_tabla, 'after'):
            view_manager.grand_total_tabla.after(100, update_opens_delayed)

def seleccionar_campanas(campanas, input_str):
    """
    Selecciona campañas basándose en criterios de búsqueda.
    Soporta búsqueda por índice, código de país o prefijo.
    """
    seleccionados = []
    vistos = set()
    
    tokens = [t.strip().lower() for t in input_str.split(",") if t.strip()]
    indices = [int(token) - 1 for token in tokens if token.isdigit()]
    
    for token in tokens:
        if len(token) == 2 and token in ALLOWED_CODES:
            # Búsqueda por código de país
            for camp in campanas:
                idx, cid, name, send_time, *_ = camp
                partes = name.split("_")
                if len(partes) > 1 and partes[-1].strip().lower() == token:
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
        elif not token.isdigit():
            # Búsqueda por prefijo
            for camp in campanas:
                idx, cid, name, send_time, *_ = camp
                partes = name.split("_")
                if partes and token in partes[0].lower():
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
    
    # Búsqueda por índice
    for idx in indices:
        if 0 <= idx < len(campanas):
            camp = campanas[idx]
            _, cid, _, send_time, *_ = camp
            key = (cid, send_time)
            if key not in vistos:
                vistos.add(key)
                seleccionados.append(camp)
    
    return sorted(seleccionados, key=lambda x: x[0])