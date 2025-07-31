# config.py
import os
from secrets import OPEN_EXCHANGE_API_KEY, KLAVIYO_API_KEY  # Importamos las claves desde secrets.py

# Claves API
API_KEY = OPEN_EXCHANGE_API_KEY
API_KEY_KLAVIYO = KLAVIYO_API_KEY

# URLs de Klaviyo agrupadas (solo las que se usan)
KLAVIYO_URLS = {
    "CAMPAIGN_VALUES_REPORT": "https://a.klaviyo.com/api/campaign-values-reports/",
    "CAMPAIGN_DETAILS": "https://a.klaviyo.com/api/campaigns/",
    "CAMPAIGN_MESSAGES": "https://a.klaviyo.com/api/campaign-messages/",
    "METRIC_AGGREGATES": "https://a.klaviyo.com/api/metric-aggregates",
    "METRICS": "https://a.klaviyo.com/api/metrics",
    "EVENTS": "https://a.klaviyo.com/api/events",
    "LISTS": "https://a.klaviyo.com/api/lists/",
    "SEGMENTS": "https://a.klaviyo.com/api/segments/",
}

# URL para obtener tasas de cambio desde Open Exchange Rates
BASE_URL_RATES = "https://openexchangerates.org/api/latest.json"

# Lista de monedas soportadas para conversiones de tasas de cambio
CURRENCIES = ["HNL", "GTQ", "SVC", "CRC", "NIO", "JMD", "COP", "PAB", "AWG", "BBD", "TTD", "USD", "DOP"]

# Códigos de país permitidos para filtrar campañas
ALLOWED_CODES = {"hn", "gt", "sv", "pa", "co", "ni", "cr", "do", "aw", "bb", "jm", "tt", "vi"}

# Mapeo de códigos de país a monedas
COUNTRY_TO_CURRENCY = {
    "hn": "HNL", "gt": "GTQ", "sv": "SVC", "pa": "PAB", "co": "COP", "ni": "NIO",
    "cr": "CRC", "do": "DOP", "aw": "AWG", "bb": "BBD", "jm": "JMD", "tt": "TTD", "vi": "USD"
}

# Símbolos de monedas para mostrar en la interfaz
CURRENCY_SYMBOLS = {
    "HNL": "L", "GTQ": "Q", "SVC": "$", "CRC": "₡", "NIO": "C$", "JMD": "J$", "COP": "$", "PAB": "$",
    "AWG": "ƒ", "BBD": "$", "TTD": "TT$", "USD": "$", "DOP": "RD$"
}

# Encabezados para las solicitudes a la API de Klaviyo
HEADERS_KLAVIYO = {
    "accept": "application/vnd.api+json",
    "content-type": "application/vnd.api+json",
    "revision": "2025-01-15",
    "Authorization": f"Klaviyo-API-Key {API_KEY_KLAVIYO}"
}

# Validación de consistencia
assert set(COUNTRY_TO_CURRENCY.keys()) == ALLOWED_CODES, "Mismatch between COUNTRY_TO_CURRENCY and ALLOWED_CODES"
assert set(COUNTRY_TO_CURRENCY.values()).issubset(CURRENCIES), "Some currencies in COUNTRY_TO_CURRENCY are not in CURRENCIES"