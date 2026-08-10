import re
from decimal import Decimal


def parse_amount(text):
    """
    Detecta cantidades en diferentes formatos:

    15000
    15.000
    15,000
    15 mil
    15k
    15 lucas
    15 mil pesos
    $15.000
    """

    text = text.lower().strip()

    # --------------------------------
    # MILLONES
    # --------------------------------

    match = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(millón|millones|millon|millones)\b',
        text
    )

    if match:
        number = match.group(1).replace(",", ".")

        return Decimal(number) * 1_000_000

    # --------------------------------
    # MILES
    # --------------------------------

    match = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(mil|k|lucas)\b',
        text
    )

    if match:
        number = match.group(1).replace(",", ".")

        return Decimal(number) * 1000

    # --------------------------------
    # FORMATO 1.500.000
    # --------------------------------

    match = re.search(
        r'\$?\s*(\d{1,3}(?:\.\d{3})+)',
        text
    )

    if match:
        number = (
            match.group(1)
            .replace(".", "")
        )

        return Decimal(number)

    # --------------------------------
    # FORMATO 1,500,000
    # --------------------------------

    match = re.search(
        r'\$?\s*(\d{1,3}(?:,\d{3})+)',
        text
    )

    if match:
        number = (
            match.group(1)
            .replace(",", "")
        )

        return Decimal(number)

    # --------------------------------
    # NÚMERO SIMPLE
    # --------------------------------

    match = re.search(
        r'\$?\s*(\d+)',
        text
    )

    if match:
        return Decimal(match.group(1))

    return None


def detect_transaction_type(text):
    text = text.lower()

    income_words = [
        "recibí",
        "recibi",
        "ingresó",
        "ingreso",
        "me consignaron",
        "consignaron",
        "salario",
        "sueldo",
        "pago recibido",
        "me pagaron",
    ]

    expense_words = [
        "gasté",
        "gaste",
        "gasté",
        "compré",
        "compre",
        "pagué",
        "pague",
        "comprar",
        "gasto",
        "pago",
    ]

    for word in income_words:
        if word in text:
            return "INCOME"

    for word in expense_words:
        if word in text:
            return "EXPENSE"

    return None


def detect_category(text):
    text = text.lower()

    categories = {
        "alimentación": [
            "comida",
            "almuerzo",
            "desayuno",
            "cena",
            "comida",
            "restaurante",
            "mercado",
        ],

        "transporte": [
            "transporte",
            "bus",
            "buseta",
            "taxi",
            "uber",
            "indrive",
            "gasolina",
            "pasaje",
        ],

        "arriendo": [
            "arriendo",
            "alquiler",
        ],

        "entretenimiento": [
            "cine",
            "juego",
            "videojuego",
            "entretenimiento",
        ],

        "salud": [
            "medicina",
            "farmacia",
            "médico",
            "medico",
            "salud",
        ],

        "ropa": [
            "ropa",
            "camisa",
            "pantalón",
            "zapatos",
            "tenis",
        ],

        "tecnología": [
            "celular",
            "computador",
            "pc",
            "audífonos",
            "audifonos",
            "tecnología",
            "tecnologia",
        ],

        "salario": [
            "salario",
            "sueldo",
            "nómina",
            "nomina",
            "pago",
        ],
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return None


def parse_message(text):
    """
    Convierte un mensaje del usuario
    en información estructurada.
    """

    return {
        "type": detect_transaction_type(text),
        "amount": parse_amount(text),
        "category": detect_category(text),
        "original_text": text,
    }