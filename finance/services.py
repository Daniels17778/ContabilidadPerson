from decimal import Decimal
from django.db import transaction

from .models import Account, Category, Transaction


@transaction.atomic
def register_expense(
    user,
    account,
    category,
    amount,
    description="",
    date=None,
):
    amount = Decimal(amount)

    if amount <= 0:
        raise ValueError("El monto debe ser mayor que cero.")

    if account.user != user:
        raise ValueError("La cuenta no pertenece al usuario.")

    if category.user != user:
        raise ValueError("La categoría no pertenece al usuario.")

    if category.type != "EXPENSE":
        raise ValueError(
            "La categoría seleccionada no es de gastos."
        )

    if account.balance < amount:
        raise ValueError(
            "Saldo insuficiente en la cuenta."
        )

    account.balance -= amount
    account.save(update_fields=["balance", "updated_at"])

    transaction_obj = Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        type="EXPENSE",
        amount=amount,
        description=description,
        date=date,
    )

    return transaction_obj

@transaction.atomic
def register_income(
    user,
    account,
    category,
    amount,
    description="",
    date=None,
):
    amount = Decimal(amount)

    if amount <= 0:
        raise ValueError("El monto debe ser mayor que cero.")

    if account.user != user:
        raise ValueError("La cuenta no pertenece al usuario.")

    if category.user != user:
        raise ValueError("La categoría no pertenece al usuario.")

    if category.type != "INCOME":
        raise ValueError(
            "La categoría seleccionada no es de ingresos."
        )

    account.balance += amount
    account.save(update_fields=["balance", "updated_at"])

    transaction_obj = Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        type="INCOME",
        amount=amount,
        description=description,
        date=date,
    )

    return transaction_obj