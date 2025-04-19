# exchange_rates.py
import requests
from config import API_KEY, BASE_URL_RATES

def obtener_tasas_de_cambio(base="USD", symbols=None):
    """
    Obtiene las tasas de cambio más recientes de Open Exchange Rates.
    
    :param base: Moneda base (por defecto 'USD').
    :param symbols: Lista de monedas a consultar (opcional).
    :return: Diccionario con tasas de cambio.
    """
    try:
        # Construir la URL y los parámetros
        params = {
            "app_id": API_KEY,
            "base": base,
        }
        if symbols:
            params["symbols"] = ",".join(symbols)
        
        response = requests.get(BASE_URL_RATES, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Obtener las tasas de cambio
        rates = data.get("rates", {})
        return rates
    
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener tasas de cambio: {e}")
        return {}