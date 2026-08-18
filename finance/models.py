from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    CATEGORY_TYPES = [
        ("INCOME", "Ingreso"),
        ("EXPENSE", "Gasto"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories"
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.icon} {self.name}"


class Account(models.Model):
    ACCOUNT_TYPES = [
        ("CASH", "Efectivo"),
        ("BANK", "Cuenta bancaria"),
        ("NEQUI", "Nequi"),
        ("DIGITAL", "Billetera digital"),
        ("OTHER", "Otro"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="accounts"
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.balance:,.0f}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("INCOME", "Ingreso"),
        ("EXPENSE", "Gasto"),
        ("TRANSFER", "Transferencia"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transfer_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions"
    )

    type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - ${self.amount:,.0f}"


class ReservedFund(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reserved_funds"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="reserved_funds"
    )

    name = models.CharField(max_length=100)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    purpose = models.CharField(
        max_length=255,
        blank=True
    )

    deadline = models.DateField(
        null=True,
        blank=True
    )

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.amount:,.0f}"


class Budget(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="budgets"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()

    limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "category", "month", "year")

    def __str__(self):
        return (
            f"{self.category.name} - "
            f"{self.month}/{self.year}"
        )


class SavingsGoal(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="savings_goals"
    )

    name = models.CharField(max_length=100)

    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    deadline = models.DateField(
        null=True,
        blank=True
    )

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.current_amount:,.0f}"


class Debt(models.Model):
    DEBT_STATUS = [
        ("PENDING", "Pendiente"),
        ("PARTIAL", "Pago parcial"),
        ("PAID", "Pagada"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="debts"
    )

    name = models.CharField(max_length=100)

    creditor = models.CharField(
        max_length=100,
        blank=True
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=DEBT_STATUS,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.total_amount:,.0f}"