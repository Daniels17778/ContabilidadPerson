import re
import unicodedata
from decimal import Decimal


def normalize(text):
    """
    Pasa el texto a minúsculas y le quita las tildes,
    para que "cuánto" y "cuanto" (o "gasté" y "gaste")
    se traten como lo mismo sin tener que listar cada
    variante a mano.
    """

    text = text.lower().strip()

    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )

    return text


def contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


# --------------------------------------------------------
# CATEGORÍAS
#
# Única fuente de verdad. Antes existían dos diccionarios
# de categorías (uno en detect_category y otro en
# detect_category_query) que se fueron desincronizando.
# Ahora ambas funciones usan este mismo diccionario.
#
# Las palabras clave van SIN tilde porque el texto de
# entrada se normaliza antes de comparar.
# --------------------------------------------------------

CATEGORY_KEYWORDS = {
    "alimentación": [
        "comida",
        "almuerzo",
        "desayuno",
        "cena",
        "restaurante",
        "mercado",
        "domicilio",
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
        "peaje",
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
        "streaming",
        "netflix",
    ],
    "salud": [
        "medicina",
        "farmacia",
        "medico",
        "salud",
        "droguería",
        "eps",
    ],
    "ropa": [
        "ropa",
        "camisa",
        "pantalon",
        "zapatos",
        "tenis",
    ],
    "tecnología": [
        "celular",
        "computador",
        "pc",
        "audifonos",
        "tecnologia",
        "cargador",
    ],
    # Nota: "pago" a propósito NO está aquí porque es
    # demasiado genérico (aparece en casi cualquier frase
    # de gasto) y hacía que cosas como "hice un pago de
    # arriendo" se clasificaran como salario.
    "salario": [
        "salario",
        "sueldo",
        "nomina",
    ],
}


def detect_category(text):
    text = normalize(text)

    for category, keywords in CATEGORY_KEYWORDS.items():
        if contains_any(text, keywords):
            return category

    return None


def detect_category_query(text):
    """
    Solo detecta categoría cuando el mensaje es explícitamente
    una consulta ("cuánto gasté en...", "gastos en...").
    Reutiliza el mismo diccionario que detect_category.
    """

    text = normalize(text)

    query_words = [
        "cuanto gaste en",
        "cuanto he gastado en",
        "cuanto llevo gastado en",
        "gasto en",
        "gastos en",
    ]

    if not contains_any(text, query_words):
        return None

    return detect_category(text)


# --------------------------------------------------------
# MONTOS
# --------------------------------------------------------

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

    text = normalize(text)

    # --------------------------------
    # MILLONES
    # --------------------------------

    match = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(millon|millones)\b',
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
        number = match.group(1).replace(".", "")
        return Decimal(number)

    # --------------------------------
    # FORMATO 1,500,000
    # --------------------------------

    match = re.search(
        r'\$?\s*(\d{1,3}(?:,\d{3})+)',
        text
    )

    if match:
        number = match.group(1).replace(",", "")
        return Decimal(number)

    # --------------------------------
    # NÚMERO SIMPLE
    # --------------------------------

    match = re.search(r'\$?\s*(\d+)', text)

    if match:
        return Decimal(match.group(1))

    return None


# --------------------------------------------------------
# TIPO DE MOVIMIENTO
# --------------------------------------------------------

INCOME_WORDS = [
    "recibi",
    "ingreso",
    "me consignaron",
    "consignaron",
    "salario",
    "sueldo",
    "pago recibido",
    "me pagaron",
    "me depositaron",
]

# Palabras "fuertes": si aparecen, es gasto casi seguro.
# Nota: "pago" se revisa DESPUÉS de INCOME_WORDS en
# detect_transaction_type, así que "recibí un pago" sigue
# clasificando bien como INCOME. Aquí solo cubre casos
# como "hice un pago de arriendo".
EXPENSE_WORDS = [
    "gaste",
    "compre",
    "pague",
    "comprar",
    "gasto",
    "pago",
]


def detect_transaction_type(text):
    text = normalize(text)

    if contains_any(text, INCOME_WORDS):
        return "INCOME"

    if contains_any(text, EXPENSE_WORDS):
        return "EXPENSE"

    return None


TRANSFER_WORDS = [
    "pase",
    "transferi",
    "movi",
    "envie",
]


def detect_transfer(text):
    text = normalize(text)
    return contains_any(text, TRANSFER_WORDS)


# --------------------------------------------------------
# CUENTAS
# --------------------------------------------------------

BALANCE_WORDS = [
    "cuanto tengo",
    "cuanta plata tengo",
    "cuanto dinero tengo",
    "cual es mi saldo",
    "mi saldo",
    "mis cuentas",
    "cuanto hay",
]


def detect_balance_query(text):
    text = normalize(text)
    return contains_any(text, BALANCE_WORDS)


def parse_balance_account(text):
    text = normalize(text)

    accounts = ["nequi", "bancolombia", "efectivo"]

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

    text = normalize(text)

    match = re.search(
        r"(?:de|desde)\s+(.+?)\s+(?:a|hacia)\s+(.+)",
        text,
    )

    if not match:
        return None, None

    source = match.group(1).strip()
    destination = match.group(2).strip()

    return source, destination


# --------------------------------------------------------
# CONSULTAS
# --------------------------------------------------------

QUERY_BALANCE_WORDS = [
    "cuanto tengo",
    "saldo",
    "dinero tengo",
    "plata tengo",
]

QUERY_EXPENSE_WORDS = [
    "cuanto gaste",
    "cuanto he gastado",
    "total de gastos",
    "mis gastos",
]

QUERY_INCOME_WORDS = [
    "cuanto recibi",
    "cuanto he recibido",
    "total de ingresos",
    "mis ingresos",
]

QUERY_SUMMARY_WORDS = [
    "como estan mis gastos",
    "como estuvieron mis gastos",
    "como estan mis finanzas",
    "como estuvieron mis finanzas",
    "como van mis finanzas",
    "resumen de mis gastos",
    "resumen de mis finanzas",
    "resumen financiero",
]


def detect_query_type(text):
    text = normalize(text)

    if contains_any(text, QUERY_BALANCE_WORDS):
        return "BALANCE"

    if contains_any(text, QUERY_SUMMARY_WORDS):
        return "MONTH_SUMMARY"

    if contains_any(text, QUERY_EXPENSE_WORDS):
        return "EXPENSE_TOTAL"

    if contains_any(text, QUERY_INCOME_WORDS):
        return "INCOME_TOTAL"

    return None


PERIOD_MAP = [
    ("hoy", "TODAY"),
    ("ayer", "YESTERDAY"),
    ("esta semana", "WEEK"),
    ("mes pasado", "LAST_MONTH"),
    ("este mes", "MONTH"),
    ("mes actual", "MONTH"),
]


def detect_period(text):
    text = normalize(text)

    for phrase, period in PERIOD_MAP:
        if phrase in text:
            return period

    return None


TOP_EXPENSE_PHRASES = [
    "en que estoy gastando mas",
    "cual es mi mayor gasto",
    "en que categoria gasto mas",
    "en que gasto mas",
    "donde gasto mas",
]


def detect_top_expense_query(text):
    text = normalize(text)
    return contains_any(text, TOP_EXPENSE_PHRASES)


EXPENSES_BREAKDOWN_PHRASES = [
    "en que gaste",
    "en que he gastado",
    "en que estoy gastando",
    "como estan mis gastos",
    "desglose de gastos",
    "desglose mis gastos",
]


def detect_expenses_breakdown_query(text):
    text = normalize(text)
    return contains_any(text, EXPENSES_BREAKDOWN_PHRASES)


INCOME_BREAKDOWN_PHRASES = [
    "en que recibi",
    "en que he recibido",
    "de donde vienen mis ingresos",
    "de donde viene mi dinero",
    "desglose de ingresos",
    "desglose de mis ingresos",
    "en que recibi plata",
]


def detect_income_breakdown_query(text):
    text = normalize(text)
    return contains_any(text, INCOME_BREAKDOWN_PHRASES)


# --------------------------------------------------------
# PUNTO DE ENTRADA
# --------------------------------------------------------

def parse_message(text):
    period = detect_period(text)

    # --------------------------------
    # CONSULTA POR CATEGORÍA
    # --------------------------------

    category_query = detect_category_query(text)

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
    # DESGLOSES Y CONSULTAS ESPECIALES
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
    # OTRAS CONSULTAS (saldo, resumen, totales)
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