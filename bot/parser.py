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

def detect_transfer(text):
    text = text.lower()

    transfer_words = [
        "pasé",
        "pase",
        "transferí",
        "transferi",
        "moví",
        "movi",
        "envié",
        "envie",
    ]

    for word in transfer_words:
        if word in text:
            return True

    return False

def detect_balance_query(text):
    text = text.lower()

    balance_words = [
        "cuánto tengo",
        "cuanto tengo",
        "cuánta plata tengo",
        "cuanta plata tengo",
        "cuánto dinero tengo",
        "cuanto dinero tengo",
        "cuál es mi saldo",
        "cual es mi saldo",
        "mi saldo",
        "mis cuentas",
        "cuánto hay",
        "cuanto hay",
    ]

    for phrase in balance_words:
        if phrase in text:
            return True

    return False

def parse_balance_account(text):
    text = text.lower()

    accounts = [
        "nequi",
        "bancolombia",
        "efectivo",
    ]

    for account in accounts:
        if account in text:
            return account

    return None

def parse_transfer_accounts(text):
    """
    Detecta frases como:

    de Bancolombia a Nequi
    desde Nequi hacia Bancolombia
    """

    text = text.lower()

    match = re.search(
        r"(?:de|desde)\s+(.+?)\s+(?:a|hacia)\s+(.+)",
        text,
    )

    if not match:
        return None, None

    source = match.group(1).strip()
    destination = match.group(2).strip()

    return source, destination

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
    category_query = detect_category_query(text)
    period = detect_period(text)

    # --------------------------------
    # CONSULTA POR CATEGORÍA
    # --------------------------------

    if category_query:
        return {
            "type": "CATEGORY_TOTAL",
            "amount": None,
            "category": category_query,
            "source_account": None,
            "destination_account": None,
            "account": None,
            "period": period,
            "original_text": text,
        }

    # --------------------------------
    # DESGLOSE DE INGRESOS
    # --------------------------------

    if detect_income_breakdown_query(text):
        return {
            "type": "INCOME_BREAKDOWN",
            "amount": None,
            "category": None,
            "source_account": None,
            "destination_account": None,
            "account": None,
            "period": period,
            "original_text": text,
        }

    if detect_top_expense_query(text):
        return {
            "type": "TOP_EXPENSE",
            "amount": None,
            "category": None,
            "source_account": None,
            "destination_account": None,
            "account": None,
            "period": period,
            "original_text": text,
        }

    if detect_expenses_breakdown_query(text):
        return {
            "type": "EXPENSES_BREAKDOWN",
            "amount": None,
            "category": None,
            "source_account": None,
            "destination_account": None,
            "account": None,
            "period": period,
            "original_text": text,
        }

    # --------------------------------
    # OTRAS CONSULTAS
    # --------------------------------

    query_type = detect_query_type(text)

    if query_type:
        return {
            "type": query_type,
            "amount": None,
            "category": None,
            "source_account": None,
            "destination_account": None,
            "account": None,
            "period": period,
            "original_text": text,
        }

    # --------------------------------
    # TRANSFERENCIAS
    # --------------------------------

    source_account, destination_account = parse_transfer_accounts(text)

    if detect_transfer(text):
        transaction_type = "TRANSFER"
    else:
        transaction_type = detect_transaction_type(text)

    return {
        "type": transaction_type,
        "amount": parse_amount(text),
        "category": detect_category(text),
        "source_account": source_account,
        "destination_account": destination_account,
        "account": None,
        "period": period,
        "original_text": text,
    }

    
def detect_query_type(text):
    text = text.lower()

    balance_words = [
        "cuánto tengo",
        "cuanto tengo",
        "saldo",
        "dinero tengo",
        "plata tengo",
    ]

    expense_words = [
        "cuánto gasté",
        "cuanto gaste",
        "cuánto he gastado",
        "cuanto he gastado",
        "total de gastos",
        "mis gastos",
    ]

    income_words = [
        "cuánto recibí",
        "cuanto recibi",
        "cuánto he recibido",
        "cuanto he recibido",
        "total de ingresos",
        "mis ingresos",
    ]

    summary_words = [
        # Gastos
        "cómo están mis gastos",
        "como estan mis gastos",
        "cómo estuvieron mis gastos",
        "como estuvieron mis gastos",

        # Finanzas
        "cómo están mis finanzas",
        "como estan mis finanzas",
        "cómo estuvieron mis finanzas",
        "como estuvieron mis finanzas",

        # Otras formas
        "cómo van mis finanzas",
        "como van mis finanzas",
        "resumen de mis gastos",
        "resumen de mis finanzas",
        "resumen financiero",
    ]

    if any(word in text for word in balance_words):
        return "BALANCE"

    if any(word in text for word in summary_words):
        return "MONTH_SUMMARY"

    if any(word in text for word in expense_words):
        return "EXPENSE_TOTAL"

    if any(word in text for word in income_words):
        return "INCOME_TOTAL"

    return None


def detect_category_query(text):
    text = text.lower()

    query_words = [
        "cuánto gasté en",
        "cuanto gaste en",
        "cuánto he gastado en",
        "cuanto he gastado en",
        "cuánto llevo gastado en",
        "cuanto llevo gastado en",
        "gasto en",
        "gastos en",
    ]

    if not any(word in text for word in query_words):
        return None

    categories = {
        "alimentación": [
            "alimentación",
            "alimentacion",
            "comida",
            "almuerzo",
            "desayuno",
            "cena",
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
            "entretenimiento",
            "cine",
            "juego",
            "videojuego",
        ],

        "salud": [
            "salud",
            "medicina",
            "farmacia",
            "médico",
            "medico",
        ],

        "ropa": [
            "ropa",
            "camisa",
            "pantalón",
            "zapatos",
            "tenis",
        ],

        "tecnología": [
            "tecnología",
            "tecnologia",
            "celular",
            "computador",
            "pc",
            "audífonos",
            "audifonos",
        ],
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return None

def detect_period(text):
    text = text.lower()

    if "hoy" in text:
        return "TODAY"

    if "ayer" in text:
        return "YESTERDAY"

    if "esta semana" in text:
        return "WEEK"

    if "este mes" in text or "mes actual" in text:
        return "MONTH"

    if "mes pasado" in text:
        return "LAST_MONTH"

    return None

def detect_top_expense_query(text):
    text = text.lower()

    phrases = [
        "en qué estoy gastando más",
        "en que estoy gastando mas",
        "cuál es mi mayor gasto",
        "cual es mi mayor gasto",
        "en qué categoría gasto más",
        "en que categoria gasto mas",
        "en qué gasto más",
        "en que gasto mas",
        "dónde gasto más",
        "donde gasto mas",
    ]

    for phrase in phrases:
        if phrase in text:
            return True

    return False

def detect_expenses_breakdown_query(text):
    text = text.lower()

    phrases = [
        "en qué gasté",
        "en que gaste",
        "en qué he gastado",
        "en que he gastado",
        "en qué estoy gastando",
        "en que estoy gastando",
        "cómo están mis gastos",
        "como estan mis gastos",
        "desglose de gastos",
        "desglose mis gastos",
    ]

    for phrase in phrases:
        if phrase in text:
            return True

    return False

def detect_income_breakdown_query(text):
    text = text.lower()

    phrases = [
        "en qué recibí",
        "en que recibi",
        "en qué he recibido",
        "en que he recibido",
        "de dónde vienen mis ingresos",
        "de donde vienen mis ingresos",
        "de dónde viene mi dinero",
        "de donde viene mi dinero",
        "desglose de ingresos",
        "desglose de mis ingresos",
        "en qué recibí plata",
        "en que recibi plata",
    ]

    return any(phrase in text for phrase in phrases)