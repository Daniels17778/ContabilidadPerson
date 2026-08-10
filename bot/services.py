from datetime import date

from django.db import transaction

from finance.models import Account, Category
from finance.services import register_expense, register_income

from .parser import parse_message

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
        amount = parsed["amount"]
        category_name = parsed["category"]
        account = find_account(user, text)

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

            else:

                transaction_obj = register_income(
                    user=user,
                    account=conversation.pending_account,
                    category=conversation.pending_category,
                    amount=conversation.pending_amount,
                    description=conversation.pending_description,
                    date=date.today(),
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

            else:

                response = (
                    f"✅ Ingreso registrado.\n"
                    f"💰 ${amount:,.0f}\n"
                    f"🏷️ {category.name}\n"
                    f"🏦 {account.name}\n"
                    f"💰 Saldo: ${account.balance:,.0f}"
                )

            # Reiniciar conversación

            conversation.state = "IDLE"
            conversation.pending_type = ""
            conversation.pending_amount = None
            conversation.pending_category = None
            conversation.pending_account = None
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