def format_ecuador_whatsapp(phone: str) -> str:
    """
    Estandariza un número de teléfono de Ecuador al formato internacional de WhatsApp: +5939XXXXXXXX.
    Remueve ceros locales iniciales, espacios y caracteres especiales.
    """
    if not phone:
        return "+593987654321"
    
    # Conservar solo los dígitos
    digits = "".join(c for c in phone if c.isdigit())
    
    # Remover ceros a la izquierda del código internacional
    if digits.startswith("00"):
        digits = digits[2:]
        
    # Caso 1: Formato local '0984183790' (10 dígitos empezando con 0)
    if digits.startswith("09") and len(digits) == 10:
        return f"+593{digits[1:]}"
        
    # Caso 2: Formato local sin cero '984183790' (9 dígitos empezando con 9)
    if digits.startswith("9") and len(digits) == 9:
        return f"+593{digits}"
        
    # Caso 3: Formato incorrecto con cero intermedio '5930984183790' (13 dígitos)
    if digits.startswith("59309") and len(digits) == 13:
        return f"+5939{digits[5:]}"
        
    # Caso 4: Si ya tiene 12 dígitos y empieza con 593, está correcto
    if digits.startswith("593") and len(digits) == 12:
        return f"+{digits}"
        
    # Fallback general para Ecuador si tiene 9 o 10 dígitos
    if len(digits) == 10 and digits.startswith("0"):
        return f"+593{digits[1:]}"
    if len(digits) == 9:
        return f"+593{digits}"
        
    return f"+{digits}" if digits else "+593987654321"
