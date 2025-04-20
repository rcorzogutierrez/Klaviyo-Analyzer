# campaign_logic.py
import requests
from collections import defaultdict
from datetime import datetime, timezone
from config import ALLOWED_CODES, COUNTRY_TO_CURRENCY, CURRENCY_SYMBOLS, HEADERS_KLAVIYO, CURRENCIES, KLAVIYO_URLS
from klaviyo_api import get_campaign_metrics, get_campaign_details, preload_campaign_details, query_metric_aggregates_post
from exchange_rates import obtener_tasas_de_cambio
from utils import format_number, format_percentage

def obtener_campanas(list_start_date, list_end_date, update_callback):
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
    metrics = get_campaign_metrics(list_start_date, list_end_date, conversion_metric_id, update_callback)

    if not metrics:
        if update_callback:
            update_callback("No se encontraron campañas en el rango de fechas seleccionado.")
        return None, "No se encontraron campañas en el rango de fechas seleccionado."

    if update_callback:
        update_callback("Obteniendo detalles de las campañas...")
    campaign_ids = [result['groupings']['campaign_id'] for result in metrics]
    campaign_details_cache = {}
    preload_campaign_details(campaign_ids, campaign_details_cache, update_callback)

    if update_callback:
        update_callback("Procesando datos de campañas, métricas de órdenes completadas y tasas de cambio...")
    filtered_campaigns = []
    start_dt = datetime.strptime(f"{list_start_date}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_dt = datetime.strptime(f"{list_end_date}T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")

    # Determinar las monedas necesarias basadas en los países de las campañas
    country_codes = set()
    for result in metrics:
        campaign_id = result['groupings']['campaign_id']
        name, _, _, _, _ = get_campaign_details(campaign_id, campaign_details_cache, update_callback)
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

    for result in metrics:
        campaign_id = result['groupings']['campaign_id']
        name, send_time, subject, preview, template_id = get_campaign_details(campaign_id, campaign_details_cache, update_callback)
        open_rate = round(result['statistics']['open_rate'] * 100, 2)
        click_rate = round(result['statistics']['click_rate'] * 100, 2)
        delivered = int(result['statistics']['delivered'])

        try:
            send_dt = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S") if send_time != 'N/A' else None
            if send_dt and start_dt <= send_dt <= end_dt:
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
                
                filtered_campaigns.append({
                    'campaign_id': campaign_id,
                    'campaign_name': name,
                    'send_time': send_time,
                    'open_rate': open_rate,
                    'click_rate': click_rate,
                    'delivered': delivered,
                    'subject_line': subject,
                    'preview_text': preview,
                    'template_id': template_id,  # Nuevo campo
                    'order_unique': order_metrics["unique"],  # Órdenes únicas
                    'order_sum_value': usd_value,  # Valor total de órdenes en USD
                    'order_sum_value_local': local_value,  # Valor en moneda local
                    'order_count': order_metrics["count"],  # Cantidad total de órdenes
                    'per_recipient': per_recipient,  # Total Value (USD) / Recibidos
                })
                if update_callback:
                    update_callback(f"Campaña filtrada: ID: {campaign_id}, Nombre: {name}, Send Time: {send_time}, Open Rate: {open_rate}%, Click Rate: {click_rate}%, Delivered: {delivered}, Unique Orders: {order_metrics['unique']}, Total Value (USD): {usd_value:.2f}, Total Value (Local): {local_value:.2f} {CURRENCY_SYMBOLS.get(currency, '$')}, Order Count: {order_metrics['count']}, Per Recipient: {per_recipient:.2f}")
        except ValueError as ve:
            if update_callback:
                update_callback(f"Error en formato de send_time para {name}: {send_time} - Error: {ve}")
            return None, f"Formato de send_time inválido para {name}: {send_time}"

    if update_callback:
        update_callback(f"Campañas filtradas totales: {len(filtered_campaigns)}")
    update_callback(f"Carga completa - Total de campañas filtradas: {len(filtered_campaigns)}")

    # Formatear las campañas para la salida esperada
    campaigns_list = [
        (idx, camp['campaign_id'], camp['campaign_name'], camp['send_time'], camp['open_rate'], camp['click_rate'], 
         camp['delivered'], camp['subject_line'], camp['preview_text'], camp['template_id'],  # Agregar template_id
         camp['order_unique'], camp['order_sum_value'], camp['order_sum_value_local'], camp['order_count'], camp['per_recipient'])
        for idx, camp in enumerate(filtered_campaigns, start=1)
    ]
    return campaigns_list, None

def agrupar_por_pais(campanas):
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, open_rate, click_rate, delivered, subject, preview, template_id, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
        partes = name.split("_")
        pais = partes[-1].strip().lower() if len(partes) > 1 else "desconocido"
        grupos[pais].append(camp)
    return grupos

def agrupar_por_fecha(campanas):
    grupos = defaultdict(list)
    for camp in campanas:
        idx, campaign_id, name, send_time, open_rate, click_rate, delivered, subject, preview, template_id, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
        try:
            date_only = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        except ValueError:
            date_only = send_time  # Mantener el valor original si no se puede parsear
        grupos[date_only].append(camp)
    return grupos

def mostrar_campanas_en_tabla(campanas, tree, grouping="País", show_local_value=True, template_ids_dict=None):
    tree.delete(*tree.get_children())  # Limpiar la tabla antes de mostrar nuevos datos
    
    # Definir las columnas (sin "TemplateID")
    columns = ("Numero", "Nombre", "FechaEnvio", "OpenRate", "ClickRate", "Recibios", "OrderUnique", "OrderSumValue", "OrderSumValueLocal", "PerRecipient", "OrderCount", "Subject", "Preview")
    tree["columns"] = columns
    tree.heading("Numero", text="#")
    tree.heading("Nombre", text="Nombre")
    tree.heading("FechaEnvio", text="Fecha de Envío")
    tree.heading("OpenRate", text="Open Rate")
    tree.heading("ClickRate", text="Click Rate")
    tree.heading("Recibios", text="Recibidos")
    tree.heading("OrderUnique", text="Unique Orders")
    tree.heading("OrderSumValue", text="Total Value (USD)")
    tree.heading("OrderSumValueLocal", text="Total Value (Local)")
    tree.heading("OrderCount", text="Order Count")
    tree.heading("Subject", text="Subject Line")
    tree.heading("Preview", text="Preview Text")
    tree.heading("PerRecipient", text="Per Recipient")

    # Ajustar anchos y alineaciones de las columnas (eliminamos TemplateID)
    tree.column("Numero", width=50, anchor="center")
    tree.column("Nombre", width=120)
    tree.column("FechaEnvio", width=100)
    tree.column("OpenRate", width=80, anchor="center")
    tree.column("ClickRate", width=80, anchor="center")
    tree.column("Recibios", width=100, anchor="center")
    tree.column("OrderUnique", width=80, anchor="center")
    tree.column("OrderSumValue", width=120, anchor="e")
    tree.column("OrderSumValueLocal", width=120 if show_local_value else 0, anchor="e", stretch=True if show_local_value else False)
    tree.column("PerRecipient", width=120, anchor="e")
    tree.column("OrderCount", width=80, anchor="center")
    tree.column("Subject", width=150)
    tree.column("Preview", width=150)

    def add_campaign_row(camp, show_local_value=True):
        idx, campaign_id, name, send_time, open_rate, click_rate, delivered, subject, preview, template_id, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
        partes = name.split("_")
        country_code = partes[-1].strip().lower() if len(partes) > 1 and partes[-1].strip().lower() in ALLOWED_CODES else "us"
        currency = COUNTRY_TO_CURRENCY.get(country_code, "USD")
        currency_symbol = CURRENCY_SYMBOLS.get(currency, "$")
        
        values = [
            idx,
            name,
            send_time,
            format_percentage(open_rate),
            format_percentage(click_rate),
            format_number(delivered),  # Separadores de miles para Recibidos
            format_number(int(order_unique)),  # Convertir a entero y agregar separadores de miles
            format_number(order_sum_value, is_currency=True),  # Separadores de miles para Total Value (USD)
        ]
        if show_local_value:
            values.append(format_number(order_sum_value_local, is_currency=True, currency_symbol=currency_symbol))  # Separadores de miles para Total Value (Local)
        else:
            values.append("")
        values.append(format_number(per_recipient, is_currency=True))  # Separadores de miles para Per Recipient
        values.extend([
            format_number(int(order_count)),  # Convertir a entero y agregar separadores de miles
            subject,
            preview,
        ])
        return values

    def calculate_subtotals(camps, show_local_value=True):
        total_delivered = 0
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
            _, _, _, _, open_rate, click_rate, delivered, _, _, _, order_unique, order_sum_value, order_sum_value_local, order_count, per_recipient = camp
            total_delivered += delivered
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
                format_number(total_delivered),  # Separadores de miles para Recibidos
                format_number(int(total_unique)),  # Convertir a entero y agregar separadores de miles
                format_number(total_sum_value, is_currency=True),  # Separadores de miles para Total Value (USD)
            ]
            if show_local_value:
                values.append(format_number(total_sum_value_local, is_currency=True, currency_symbol="$"))  # Separadores de miles para Total Value (Local)
            else:
                values.append("")
            values.append(format_number(per_recipient_weighted_avg, is_currency=True))  # Separadores de miles para Per Recipient
            values.extend([
                format_number(int(total_count)),  # Convertir a entero y agregar separadores de miles
                "",
                "",
            ])
            return values, {
                "delivered": total_delivered,
                "weighted_open": weighted_open,
                "weighted_click": weighted_click,
                "total_weight": total_weight,
                "unique": total_unique,
                "sum_value": total_sum_value,
                "count": total_count,
                "per_recipient_weighted": total_per_recipient_weighted,
                "delivered_for_weight": total_delivered_for_weight
            }
        return None, None

    # Lista para almacenar los datos de los subtotales
    all_subtotals = []

    if grouping == "País":
        grupos = agrupar_por_pais(campanas)
        for pais in sorted(grupos.keys()):
            tree.insert("", "end", values=(f"{pais.upper()}", "", "", "", "", "", "", "", "", "", "", "", ""), tags=("bold",))
            for camp in sorted(grupos[pais], key=lambda x: x[0]):
                values = add_campaign_row(camp, show_local_value)
                # Insertar la fila y asignar el campaign_id como tag
                idx, campaign_id, _, _, _, _, _, _, _, template_id, _, _, _, _, _ = camp
                item_id = tree.insert("", "end", values=values, tags=(f"campaign_{campaign_id}",))
                # Almacenar el template_id en el diccionario
                if template_ids_dict is not None:
                    if template_id is not None:
                        template_ids_dict[item_id] = template_id
            
            subtotal_values, subtotal_data = calculate_subtotals(grupos[pais], show_local_value)
            if subtotal_values:
                tree.insert("", "end", values=subtotal_values, tags=("bold",))
                all_subtotals.append(subtotal_data)
            tree.insert("", "end", values=("", "", "", "", "", "", "", "", "", "", "", "", ""))
    else:  # Fecha
        grupos = agrupar_por_fecha(campanas)
        for fecha in sorted(grupos.keys()):
            tree.insert("", "end", values=(fecha, "", "", "", "", "", "", "", "", "", "", "", ""), tags=("bold",))
            for camp in sorted(grupos[fecha], key=lambda x: x[0]):
                values = add_campaign_row(camp, show_local_value=False)
                # Insertar la fila y asignar el campaign_id como tag
                idx, campaign_id, _, _, _, _, _, _, _, template_id, _, _, _, _, _ = camp
                item_id = tree.insert("", "end", values=values, tags=(f"campaign_{campaign_id}",))
                # Almacenar el template_id en el diccionario
                if template_ids_dict is not None:
                    if template_id is not None:
                        template_ids_dict[item_id] = template_id
            
            subtotal_values, subtotal_data = calculate_subtotals(grupos[fecha], show_local_value=False)
            if subtotal_values:
                tree.insert("", "end", values=subtotal_values, tags=("bold",))
                all_subtotals.append(subtotal_data)
            tree.insert("", "end", values=("", "", "", "", "", "", "", "", "", "", "", "", ""))

    return all_subtotals

def seleccionar_campanas(campanas, input_str):
    seleccionados = []
    vistos = set()
    
    tokens = [t.strip().lower() for t in input_str.split(",") if t.strip()]
    indices = [int(token) - 1 for token in tokens if token.isdigit()]
    
    for token in tokens:
        if len(token) == 2 and token in ALLOWED_CODES:
            for camp in campanas:
                idx, cid, name, send_time, _, _, _, _, _, _, _, _, _, _, _ = camp
                partes = name.split("_")
                if len(partes) > 1 and partes[-1].strip().lower() == token:
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
        elif not token.isdigit():
            for camp in campanas:
                idx, cid, name, send_time, _, _, _, _, _, _, _, _, _, _, _ = camp
                partes = name.split("_")
                if partes and token in partes[0].lower():
                    key = (cid, send_time)
                    if key not in vistos:
                        vistos.add(key)
                        seleccionados.append(camp)
    
    for idx in indices:
        if 0 <= idx < len(campanas):
            camp = campanas[idx]
            idx, cid, name, send_time, _, _, _, _, _, _, _, _, _, _, _ = camp
            key = (cid, send_time)
            if key not in vistos:
                vistos.add(key)
                seleccionados.append(camp)
    
    return sorted(seleccionados, key=lambda x: x[0])