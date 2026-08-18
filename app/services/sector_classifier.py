# app/services/sector_classifier.py

def classify_location(lat: float, lng: float):
    """
    Clasifica automáticamente una coordenada geográfica en una Ciudad y Sector específicos.
    Sectores soportados:
    - Quito: La Carolina (Oeste/Centro), Cumbayá (Este).
    - Guayaquil: Urdesa (Oeste), Samborondón (Este).
    """
    # Quito central: lat ~ -0.18, lng ~ -78.46
    # Guayaquil central: lat ~ -2.18, lng ~ -79.89
    
    # 1. Determinar ciudad por latitud aproximada
    if lat > -1.0: # Más cerca de Quito (-0.2) que de Guayaquil (-2.2)
        ciudad = "Quito"
        # Cumbayá está al este (longitud más grande/cerca de 0, ej: -78.43)
        # La Carolina está al oeste (longitud más pequeña, ej: -78.48)
        if lng >= -78.45:
            sector = "Cumbayá"
        else:
            sector = "La Carolina"
    else:
        ciudad = "Guayaquil"
        # Samborondón está al este (longitud más grande, ej: -79.87)
        # Urdesa está al oeste (longitud más pequeña, ej: -79.91)
        if lng >= -79.885:
            sector = "Samborondón"
        else:
            sector = "Urdesa"
            
    return ciudad, sector
