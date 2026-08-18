from datetime import date
from decimal import Decimal

from django.db import transaction

from finance.models import Account, Category
from finance.services import (
    get_category_period_total,
    get_expenses_by_category,
    register_expense,
    register_income,
    transfer_money,
    get_transaction_total,
    get_current_month_summary,
    get_top_expense_category,
    get_period_dates,
    get_income_by_category,
)

from .parser import parse_message, parse_amount, detect_category

from .models import Conversation, ConversationMessage


@transaction.atomic
def process_message(user, text, account=None):
    """
    Procesa un mensaje financiero y ejecuta
    la operación correspondiente.
    """

    parsed = parse_message(text)

    transaction_type = parsed["type"]
    amount = parsed["amount"]
    category_name = parsed["category"]

    if transaction_type is None:
        raise ValueError(
            "No pude determinar si se trata de un ingreso o un gasto."
        )

    if amount is None:
        raise ValueError(
            "No pude encontrar el monto del movimiento."
        )

    if category_name is None:
        raise ValueError(
            "No pude determinar la categoría."
        )

    if account is None:
        raise ValueError(
            "Necesito saber en qué cuenta realizar el movimiento."
        )

    category = Category.objects.filter(
        user=user,
        name__iexact=category_name,
        is_active=True,
    ).first()

    if category is None:
        raise ValueError(
            f"No existe una categoría llamada '{category_name}'."
        )

    if transaction_type == "EXPENSE":

        transaction_obj = register_expense(
            user=user,
            account=account,
            category=category,
            amount=amount,
            description=text,
            date=date.today(),
        )

        account.refresh_from_db()

        return {
            "success": True,
            "type": "EXPENSE",
            "amount": amount,
            "category": category.name,
            "account": account.name,
            "balance": account.balance,
            "transaction": transaction_obj,
        }

    if transaction_type == "INCOME":

        transaction_obj = register_income(
            user=user,
            account=account,
            category=category,
            amount=amount,
            description=text,
            date=date.today(),
        )

        account.refresh_from_db()

        return {
            "success": True,
            "type": "INCOME",
            "amount": amount,
            "category": category.name,
            "account": account.name,
            "balance": account.balance,
            "transaction": transaction_obj,
        }

    raise ValueError(
        "Tipo de movimiento no compatible."
    )
def get_conversation(user):
    conversation, created = Conversation.objects.get_or_create(
        user=user,
        defaults={
            "state": "IDLE",
        },
    )

    return conversation

def save_message(conversation, role, content):
    return ConversationMessage.objects.create(
        conversation=conversation,
        role=role,
        content=content,
    )

def find_account(user, text):
    text = text.lower().strip()

    accounts = Account.objects.filter(
        user=user,
        is_active=True,
    )

    # Primero intenta encontrar el nombre completo
    for account in accounts:
        if account.name.lower() in text:
            return account

    # Alias comunes
    aliases = {
        "nequi": ["nequi"],
        "bancolombia": ["bancolombia", "banco"],
        "efectivo": ["efectivo", "cash", "plata en efectivo"],
    }

    for account in accounts:
        account_name = account.name.lower()

        if account_name in aliases:
            for alias in aliases[account_name]:
                if alias in text:
                    return account

    return None

def get_account_balance(user, account_name=None):
    if account_name:
        account = find_account(user, account_name)

        if account is None:
            return None

        return {
            "account": account.name,
            "balance": account.balance,
        }

    accounts = Account.objects.filter(
        user=user,
        is_active=True,
    )

    total = sum(
        (account.balance for account in accounts),
        Decimal("0"),
    )

    return {
        "accounts": list(accounts),
        "total": total,
    }


def get_financial_summary(user):
    accounts = Account.objects.filter(
        user=user,
        is_active=True,
    )

    total_balance = sum(
        (account.balance for account in accounts),
        Decimal("0"),
    )

    return {
        "accounts": accounts,
        "total_balance": total_balance,
    }

def get_financial_summary_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    income = get_transaction_total(
        user=user,
        transaction_type="INCOME",
        start_date=start_date,
        end_date=end_date,
    )

    expenses = get_transaction_total(
        user=user,
        transaction_type="EXPENSE",
        start_date=start_date,
        end_date=end_date,
    )

    balance = income - expenses

    period_text = {
        None: "",
        "TODAY": " de hoy",
        "YESTERDAY": " de ayer",
        "WEEK": " de esta semana",
        "MONTH": " de este mes",
        "LAST_MONTH": " del mes pasado",
    }

    return (
        f"📊 Resumen financiero{period_text.get(period, '')}:\n"
        f"💰 Ingresos: ${income:,.0f}\n"
        f"💸 Gastos: ${expenses:,.0f}\n"
        f"📈 Balance: ${balance:,.0f}"
    )


def get_income_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    income = get_transaction_total(
        user=user,
        transaction_type="INCOME",
        start_date=start_date,
        end_date=end_date,
    )

    period_text = {
        None: "",
        "TODAY": " hoy",
        "YESTERDAY": " ayer",
        "WEEK": " esta semana",
        "MONTH": " este mes",
        "LAST_MONTH": " el mes pasado",
    }

    return (
        f"💰 Has recibido "
        f"${income:,.0f}"
        f"{period_text.get(period, '')}."
    )


def get_expense_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    expenses = get_transaction_total(
        user=user,
        transaction_type="EXPENSE",
        start_date=start_date,
        end_date=end_date,
    )

    period_text = {
        None: "",
        "TODAY": " hoy",
        "YESTERDAY": " ayer",
        "WEEK": " esta semana",
        "MONTH": " este mes",
        "LAST_MONTH": " el mes pasado",
    }

    return (
        f"💸 Has gastado "
        f"${expenses:,.0f}"
        f"{period_text.get(period, '')}."
    )

def get_top_expense_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    result = get_top_expense_category(
        user=user,
        start_date=start_date,
        end_date=end_date,
    )

    if result is None:
        if period == "MONTH":
            return "📊 No tienes gastos registrados este mes."

        if period == "TODAY":
            return "📊 No tienes gastos registrados hoy."

        if period == "WEEK":
            return "📊 No tienes gastos registrados esta semana."

        if period == "LAST_MONTH":
            return "📊 No tienes gastos registrados el mes pasado."

        return "📊 No tienes gastos registrados."

    category = result["category"]
    total = result["total"]

    if period == "MONTH":
        period_text = " este mes"
    elif period == "TODAY":
        period_text = " hoy"
    elif period == "WEEK":
        period_text = " esta semana"
    elif period == "LAST_MONTH":
        period_text = " el mes pasado"
    else:
        period_text = ""

    return (
        f"📊 Tu mayor gasto{period_text} es "
        f"{category}, con ${total:,.0f}."
    )

def get_expenses_breakdown_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    results = get_expenses_by_category(
        user=user,
        start_date=start_date,
        end_date=end_date,
    )

    if not results:
        if period == "MONTH":
            return "📊 No tienes gastos registrados este mes."

        if period == "TODAY":
            return "📊 No tienes gastos registrados hoy."

        if period == "WEEK":
            return "📊 No tienes gastos registrados esta semana."

        if period == "LAST_MONTH":
            return "📊 No tienes gastos registrados el mes pasado."

        return "📊 No tienes gastos registrados."

    if period == "MONTH":
        title = "📊 Gastos de este mes:"
    elif period == "TODAY":
        title = "📊 Gastos de hoy:"
    elif period == "WEEK":
        title = "📊 Gastos de esta semana:"
    elif period == "LAST_MONTH":
        title = "📊 Gastos del mes pasado:"
    else:
        title = "📊 Tus gastos:"

    lines = [title]

    for item in results:
        lines.append(
            f"🏷️ {item['category']}: "
            f"${item['total']:,.0f}"
        )

    total = sum(
        (item["total"] for item in results),
        Decimal("0"),
    )

    lines.append("")
    lines.append(f"💸 Total: ${total:,.0f}")

    return "\n".join(lines)

def get_income_breakdown_response(user, period=None):
    start_date, end_date = get_period_dates(period)

    results = get_income_by_category(
        user=user,
        start_date=start_date,
        end_date=end_date,
    )

    if not results:
        if period == "MONTH":
            return "📊 No tienes ingresos registrados este mes."

        if period == "TODAY":
            return "📊 No tienes ingresos registrados hoy."

        if period == "WEEK":
            return "📊 No tienes ingresos registrados esta semana."

        if period == "LAST_MONTH":
            return "📊 No tienes ingresos registrados el mes pasado."

        return "📊 No tienes ingresos registrados."

    if period == "MONTH":
        title = "📊 Ingresos de este mes:"
    elif period == "TODAY":
        title = "📊 Ingresos de hoy:"
    elif period == "WEEK":
        title = "📊 Ingresos de esta semana:"
    elif period == "LAST_MONTH":
        title = "📊 Ingresos del mes pasado:"
    else:
        title = "📊 Tus ingresos:"

    lines = [title]

    for item in results:
        lines.append(
            f"🏷️ {item['category']}: "
            f"${item['total']:,.0f}"
        )

    total = sum(
        (item["total"] for item in results),
        Decimal("0"),
    )

    lines.append("")
    lines.append(f"💰 Total: ${total:,.0f}")

    return "\n".join(lines)

def chat(user, text):
    conversation = get_conversation(user)

    save_message(
        conversation,
        "USER",
        text,
    )

    # --------------------------------
    # CONVERSACIÓN NUEVA
    # --------------------------------

    if conversation.state == "IDLE":

        parsed = parse_message(text)

        transaction_type = parsed["type"]

        if transaction_type == "TOP_EXPENSE":
            response = get_top_expense_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type == "EXPENSES_BREAKDOWN":
            response = get_expenses_breakdown_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type == "INCOME_BREAKDOWN":
            response = get_income_breakdown_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type == "MONTH_SUMMARY":
            response = get_financial_summary_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type == "CATEGORY_TOTAL":
            category_name = parsed["category"]
            period = parsed.get("period")

            response = get_category_response(
                user=user,
                category_name=category_name,
                period=period,
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response


        if transaction_type == "EXPENSE_TOTAL":
            response = get_expense_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response


        if transaction_type == "INCOME_TOTAL":
            response = get_income_response(
                user,
                parsed.get("period"),
            )

            save_message(
                conversation,
                "BOT",
             response,
            )

            return response    
        

        transaction_type = parsed["type"]
        amount = parsed["amount"]
        category_name = parsed["category"]
        account = find_account(user, text)

        source_account_name = parsed.get("source_account")
        destination_account_name = parsed.get("destination_account")

        if transaction_type == "BALANCE":

            account_name = parsed.get("account")

            if account_name:
                result = get_account_balance(
                    user,
                    account_name,
                )

                if result is None:
                    response = (
                        f"No encontré una cuenta llamada "
                        f"'{account_name}'."
                    )
                else:
                    response = (
                        f"💰 Tienes "
                        f"${result['balance']:,.0f} "
                        f"en {result['account']}."
                    )

            else:
                result = get_financial_summary(user)

                lines = ["💰 Resumen de tus cuentas:"]

                for account in result["accounts"]:
                    lines.append(
                        f"🏦 {account.name}: "
                        f"${account.balance:,.0f}"
                    )

                lines.append("")
                lines.append(
                    f"💵 Total: "
                    f"${result['total_balance']:,.0f}"
                )

                response = "\n".join(lines)

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type is None:
            response = (
                "No pude identificar si es un ingreso o un gasto."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if amount is None:
            conversation.pending_type = transaction_type
            conversation.state = "WAITING_FOR_AMOUNT"
            conversation.save()

            response = "¿Cuál es el monto?"

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if transaction_type == "TRANSFER":

            if source_account_name is None or destination_account_name is None:
                response = (
                    "Para una transferencia necesito saber "
                    "la cuenta de origen y la cuenta de destino.\n"
                    "Ejemplo: pasé 100 mil de Bancolombia a Nequi."
                )

                save_message(
                    conversation,
                    "BOT",
                    response,
                )

                return response

            source_account = find_account(
                user,
                source_account_name,
            )

            destination_account = find_account(
                user,
                destination_account_name,
            )

            if source_account is None:
                response = (
                    f"No encontré la cuenta de origen "
                    f"'{source_account_name}'."
                )

                save_message(
                    conversation,
                    "BOT",
                    response,
                )

                return response

            if destination_account is None:
                response = (
                    f"No encontré la cuenta de destino "
                    f"'{destination_account_name}'."
                )

                save_message(
                    conversation,
                    "BOT",
                    response,
                )

                return response

            if source_account == destination_account:
                response = (
                    "La cuenta de origen y destino "
                    "deben ser diferentes."
                )

                save_message(
                    conversation,
                    "BOT",
                    response,
                )

                return response

            conversation.pending_type = "TRANSFER"
            conversation.pending_amount = amount
            conversation.pending_account = source_account
            conversation.pending_transfer_account = destination_account
            conversation.pending_description = text
            conversation.state = "CONFIRMING"

            conversation.save()

            response = (
                f"¿Confirmas transferir "
                f"${amount:,.0f} "
                f"de {source_account.name} "
                f"a {destination_account.name}?"
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response
        

        if category_name is None:
            conversation.pending_type = transaction_type
            conversation.pending_amount = amount
            conversation.state = "WAITING_FOR_CATEGORY"
            conversation.save()

            response = "¿En qué categoría?"

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        category = Category.objects.filter(
            user=user,
            name__iexact=category_name,
            is_active=True,
        ).first()

        if category is None:
            response = (
                f"No tienes creada la categoría "
                f"'{category_name}'."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.pending_type = transaction_type
        conversation.pending_amount = amount
        conversation.pending_category = category

        # Si encontramos la cuenta directamente en el mensaje
        if account is not None:
            conversation.pending_account = account
            conversation.state = "CONFIRMING"

            conversation.save()

            response = (
                f"¿Confirmas "
                f"{'el gasto' if transaction_type == 'EXPENSE' else 'el ingreso'} "
                f"de ${amount:,.0f} "
                f"en {category.name} "
                f"desde {account.name}?"
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        # Si no encontramos la cuenta, preguntamos
        conversation.state = "WAITING_FOR_ACCOUNT"

        conversation.save()

        response = "¿De qué cuenta hiciste el movimiento?"

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response

     # --------------------------------
    # ESPERANDO MONTO
    # --------------------------------

    if conversation.state == "WAITING_FOR_AMOUNT":

        from .parser import parse_amount

        amount = parse_amount(text)

        if amount is None:
            response = (
                "No pude identificar el monto. "
                "Ejemplo: 20 mil, 15000 o $15.000."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.pending_amount = amount

        if conversation.pending_type == "TRANSFER":

            response = (
                f"💰 Monto recibido: ${amount:,.0f}.\n"
                "Ahora necesito saber de qué cuenta sale el dinero."
            )

            conversation.state = "WAITING_FOR_ACCOUNT"
            conversation.save()

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.state = "WAITING_FOR_CATEGORY"
        conversation.save()

        response = "¿En qué categoría?"

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response


    # --------------------------------
    # ESPERANDO CATEGORÍA
    # --------------------------------

    if conversation.state == "WAITING_FOR_CATEGORY":

        category_name = detect_category(text)

        if category_name is None:

            # También permite escribir directamente
            # el nombre de una categoría existente.

            category = Category.objects.filter(
                user=user,
                name__icontains=text.strip(),
                is_active=True,
            ).first()

            if category:
                category_name = category.name

        if category_name is None:

            response = (
                "No pude identificar la categoría. "
                "Ejemplo: transporte, comida, salud o ropa."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        category = Category.objects.filter(
            user=user,
            name__iexact=category_name,
            is_active=True,
        ).first()

        if category is None:

            response = (
                f"No tienes creada la categoría "
                f"'{category_name}'."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.pending_category = category
        conversation.state = "WAITING_FOR_ACCOUNT"
        conversation.save()

        response = "¿De qué cuenta hiciste el movimiento?"

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response   

    # --------------------------------
    # ESPERANDO CUENTA
    # --------------------------------

    if conversation.state == "WAITING_FOR_ACCOUNT":

        account = find_account(user, text)

        if account is None:

            response = (
                "No encontré esa cuenta. "
                "Escribe el nombre de la cuenta, "
                "por ejemplo: Nequi."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        # Si es una transferencia, esta cuenta es el origen
        # y todavía falta pedir la cuenta destino.

        if conversation.pending_type == "TRANSFER":

            conversation.pending_account = account
            conversation.state = "WAITING_FOR_TRANSFER_DESTINATION"
            conversation.save()

            response = (
                f"¿A qué cuenta quieres transferir "
                f"${conversation.pending_amount:,.0f}?"
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.pending_account = account
        conversation.state = "CONFIRMING"
        conversation.save()

        amount = conversation.pending_amount
        category = conversation.pending_category

        response = (
            f"¿Confirmas "
            f"{'el gasto' if conversation.pending_type == 'EXPENSE' else 'el ingreso'} "
            f"de ${amount:,.0f} "
            f"en {category.name} "
            f"desde {account.name}?"
        )

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response

    # --------------------------------
    # ESPERANDO CUENTA DESTINO (TRANSFERENCIA)
    # --------------------------------

    if conversation.state == "WAITING_FOR_TRANSFER_DESTINATION":

        destination_account = find_account(user, text)

        if destination_account is None:

            response = (
                "No encontré esa cuenta. "
                "Escribe el nombre de la cuenta destino, "
                "por ejemplo: Nequi."
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if destination_account == conversation.pending_account:

            response = (
                "La cuenta de origen y destino deben ser diferentes. "
                "¿A qué otra cuenta quieres transferir?"
            )

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        conversation.pending_transfer_account = destination_account
        conversation.state = "CONFIRMING"
        conversation.save()

        source_account = conversation.pending_account

        response = (
            f"¿Confirmas transferir "
            f"${conversation.pending_amount:,.0f} "
            f"de {source_account.name} "
            f"a {destination_account.name}?"
        )

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response

    # --------------------------------
    # CONFIRMACIÓN
    # --------------------------------

    if conversation.state == "CONFIRMING":

        normalized = text.lower().strip()

        if normalized in [
            "si",
            "sí",
            "s",
            "confirmar",
            "confirmo",
            "dale",
            "ok",
        ]:

            if conversation.pending_type == "EXPENSE":

                transaction_obj = register_expense(
                    user=user,
                    account=conversation.pending_account,
                    category=conversation.pending_category,
                    amount=conversation.pending_amount,
                    description=conversation.pending_description,
                    date=date.today(),
            )

            elif conversation.pending_type == "INCOME":

                transaction_obj = register_income(
                    user=user,
                    account=conversation.pending_account,
                    category=conversation.pending_category,
                    amount=conversation.pending_amount,
                    description=conversation.pending_description,
                    date=date.today(),
                )

            elif conversation.pending_type == "TRANSFER":

                transaction_obj = transfer_money(
                    user=user,
                    source_account=conversation.pending_account,
                    destination_account=conversation.pending_transfer_account,
                    amount=conversation.pending_amount,
                    description=conversation.pending_description,
                    date=date.today(),
                )

            else:

                raise ValueError(
                    "Tipo de movimiento no compatible."
                )

            account = conversation.pending_account
            account.refresh_from_db()

            transaction_type = conversation.pending_type
            amount = conversation.pending_amount
            category = conversation.pending_category

            if transaction_type == "EXPENSE":

                response = (
                    f"✅ Gasto registrado.\n"
                    f"💸 ${amount:,.0f}\n"
                    f"🏷️ {category.name}\n"
                    f"🏦 {account.name}\n"
                    f"💰 Saldo: ${account.balance:,.0f}"
                )

            elif transaction_type == "INCOME":

                response = (
                    f"✅ Ingreso registrado.\n"
                    f"💰 ${amount:,.0f}\n"
                    f"🏷️ {category.name}\n"
                    f"🏦 {account.name}\n"
                    f"💰 Saldo: ${account.balance:,.0f}"
                )

            elif transaction_type == "TRANSFER":

                source_account = conversation.pending_account
                destination_account = conversation.pending_transfer_account

                source_account.refresh_from_db()
                destination_account.refresh_from_db()

                response = (
                    f"✅ Transferencia realizada.\n"
                    f"💸 ${amount:,.0f}\n"
                    f"🏦 {source_account.name} → "
                    f"{destination_account.name}\n"
                    f"💰 {source_account.name}: "
                    f"${source_account.balance:,.0f}\n"
                    f"💰 {destination_account.name}: "
                    f"${destination_account.balance:,.0f}"
                )

            # Reiniciar conversación

            conversation.state = "IDLE"
            conversation.pending_type = ""
            conversation.pending_amount = None
            conversation.pending_category = None
            conversation.pending_account = None
            conversation.pending_transfer_account = None
            conversation.pending_description = ""
            

            conversation.save()

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        if normalized in [
            "no",
            "n",
            "cancelar",
            "cancela",
        ]:

            conversation.state = "IDLE"
            conversation.pending_type = ""
            conversation.pending_amount = None
            conversation.pending_category = None
            conversation.pending_account = None
            conversation.pending_description = ""

            conversation.save()

            response = "❌ Operación cancelada."

            save_message(
                conversation,
                "BOT",
                response,
            )

            return response

        response = "Responde 'sí' para confirmar o 'no' para cancelar."

        save_message(
            conversation,
            "BOT",
            response,
        )

        return response

    # --------------------------------
    # ESTADOS NO CONTROLADOS
    # --------------------------------

    conversation.state = "IDLE"
    conversation.save()

    response = "Empecemos de nuevo. ¿Qué movimiento quieres registrar?"

    save_message(
        conversation,
        "BOT",
        response,
    )

    return response

def get_category_response(user, category_name, period=None):
    total = get_category_period_total(
        user=user,
        category_name=category_name,
        period=period,
    )

    period_text = {
        None: "",
        "TODAY": " hoy",
        "YESTERDAY": " ayer",
        "WEEK": " esta semana",
        "MONTH": " este mes",
        "LAST_MONTH": " el mes pasado",
    }

    return (
        f"💸 Has gastado "
        f"${total:,.0f} "
        f"en {category_name}"
        f"{period_text.get(period, '')}."
    )