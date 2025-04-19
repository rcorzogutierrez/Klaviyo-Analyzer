# utils.py
def format_number(value, is_currency=False, currency_symbol="$"):
    if value is None or value == "":
        return ""
    try:
        num = float(value)
        if is_currency:
            formatted = f"{num:,.2f}"  # Formato con 2 decimales para moneda
            return f"{currency_symbol}{formatted}"
        else:
            formatted = f"{int(num):,}"  # Formato con separadores de miles para enteros
            return formatted
    except (ValueError, TypeError):
        return str(value)

def format_percentage(value):
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return str(value)

# ... otras funciones si las tienes ...