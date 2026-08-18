
from django.db import transaction
from django.db.models import Sum
from datetime import date as _date, timedelta
from decimal import Decimal
from django.db import models




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

    if date is None:
        date = _date.today()

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
    if date is None:
        date = _date.today()

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
@transaction.atomic
def transfer_money(
    user,
    source_account,
    destination_account,
    amount,
    description="",
    date=None,
):

    if date is None:
        date = _date.today()
            
    amount = Decimal(amount)

    if amount <= 0:
        raise ValueError(
            "El monto debe ser mayor que cero."
        )

    if source_account.user != user:
        raise ValueError(
            "La cuenta de origen no pertenece al usuario."
        )

    if destination_account.user != user:
        raise ValueError(
            "La cuenta de destino no pertenece al usuario."
        )

    if source_account == destination_account:
        raise ValueError(
            "La cuenta de origen y destino deben ser diferentes."
        )

    if source_account.balance < amount:
        raise ValueError(
            "Saldo insuficiente en la cuenta de origen."
        )

    source_account.balance -= amount
    source_account.save(
        update_fields=["balance", "updated_at"]
    )

    destination_account.balance += amount
    destination_account.save(
        update_fields=["balance", "updated_at"]
    )

    transaction_obj = Transaction.objects.create(
        user=user,
        account=source_account,
        transfer_account=destination_account,
        category=None,
        type="TRANSFER",
        amount=amount,
        description=description,
        date=date,
    )

    return transaction_obj

def get_transactions(
    user,
    transaction_type=None,
    category=None,
    account=None,
    start_date=None,
    end_date=None,
):
    queryset = Transaction.objects.filter(
        user=user,
    ).select_related(
        "account",
        "category",
    )

    if transaction_type:
        queryset = queryset.filter(
            type=transaction_type
        )

    if category:
        queryset = queryset.filter(
            category=category
        )

    if account:
        queryset = queryset.filter(
            account=account
        )

    if start_date:
        queryset = queryset.filter(
            date__gte=start_date
        )

    if end_date:
        queryset = queryset.filter(
            date__lte=end_date
        )

    return queryset.order_by(
        "-date",
        "-created_at",
    )


def get_transaction_total(
    user,
    transaction_type=None,
    category=None,
    account=None,
    start_date=None,
    end_date=None,
):
    queryset = get_transactions(
        user=user,
        transaction_type=transaction_type,
        category=category,
        account=account,
        start_date=start_date,
        end_date=end_date,
    )

    total = queryset.aggregate(
        total=Sum("amount")
    )["total"]

    return total or Decimal("0")

def get_category_total(
    user,
    category_name,
    transaction_type="EXPENSE",
    start_date=None,
    end_date=None,
):
    """
    Obtiene el total de movimientos de una categoría.
    """

    transactions = Transaction.objects.filter(
        user=user,
        type=transaction_type,
        category__name__iexact=category_name,
    )

    if start_date:
        transactions = transactions.filter(
            date__gte=start_date
        )

    if end_date:
        transactions = transactions.filter(
            date__lte=end_date
        )

    return transactions.aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0")




def get_top_expense_category(
    user,
    start_date=None,
    end_date=None,
):
    queryset = Transaction.objects.filter(
        user=user,
        type="EXPENSE",
        category__isnull=False,
    )

    if start_date:
        queryset = queryset.filter(date__gte=start_date)

    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    result = (
        queryset
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
        .first()
    )

    if result is None:
        return None

    return {
        "category": result["category__name"],
        "total": result["total"],
    }

def get_expenses_by_category(
    user,
    start_date=None,
    end_date=None,
):
    queryset = Transaction.objects.filter(
        user=user,
        type="EXPENSE",
        category__isnull=False,
    )

    if start_date:
        queryset = queryset.filter(date__gte=start_date)

    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    results = (
        queryset
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    return [
        {
            "category": item["category__name"],
            "total": item["total"],
        }
        for item in results
    ]

def get_income_by_category(
    user,
    start_date=None,
    end_date=None,
):
    transactions = Transaction.objects.filter(
        user=user,
        type="INCOME",
        category__isnull=False,
    )

    if start_date:
        transactions = transactions.filter(
            date__gte=start_date
        )

    if end_date:
        transactions = transactions.filter(
            date__lte=end_date
        )

    results = (
        transactions
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    return [
        {
            "category": item["category__name"],
            "total": item["total"],
        }
        for item in results
    ]

def get_current_month_summary(user):
    today = _date.today()

    start_date = today.replace(day=1)
    end_date = today

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

    return {
        "start_date": start_date,
        "end_date": end_date,
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
    }

def get_period_dates(period):
    today = _date.today()

    if period == "TODAY":
        return today, today

    if period == "YESTERDAY":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday

    if period == "WEEK":
        start_date = today - timedelta(days=today.weekday())
        return start_date, today

    if period == "MONTH":
        start_date = today.replace(day=1)
        return start_date, today

    if period == "LAST_MONTH":
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = (
            first_day_current_month - timedelta(days=1)
        )
        first_day_previous_month = last_day_previous_month.replace(day=1)

        return (
            first_day_previous_month,
            last_day_previous_month,
        )

    return None, None

def get_category_period_total(
    user,
    category_name,
    period=None,
):
    start_date, end_date = get_period_dates(period)

    return get_category_total(
        user=user,
        category_name=category_name,
        start_date=start_date,
        end_date=end_date,
    )