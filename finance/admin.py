from django.contrib import admin
from .models import (
    Account,
    Category,
    Transaction,
    ReservedFund,
    Budget,
    SavingsGoal,
    Debt,
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "account_type",
        "balance",
        "is_active",
    )

    list_filter = (
        "account_type",
        "is_active",
    )

    search_fields = (
        "name",
        "user__username",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "type",
        "icon",
        "is_active",
    )

    list_filter = (
        "type",
        "is_active",
    )

    search_fields = (
        "name",
        "user__username",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "type",
        "amount",
        "category",
        "account",
        "user",
    )

    list_filter = (
        "type",
        "category",
        "account",
        "date",
    )

    search_fields = (
        "description",
        "user__username",
    )

    date_hierarchy = "date"


@admin.register(ReservedFund)
class ReservedFundAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "account",
        "amount",
        "deadline",
        "is_completed",
    )

    list_filter = (
        "is_completed",
        "deadline",
    )

    search_fields = (
        "name",
        "user__username",
    )


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "user",
        "month",
        "year",
        "limit_amount",
    )

    list_filter = (
        "year",
        "month",
    )

    search_fields = (
        "category__name",
        "user__username",
    )


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "target_amount",
        "current_amount",
        "deadline",
        "is_completed",
    )

    list_filter = (
        "is_completed",
        "deadline",
    )

    search_fields = (
        "name",
        "user__username",
    )


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "creditor",
        "total_amount",
        "paid_amount",
        "status",
        "due_date",
    )

    list_filter = (
        "status",
        "due_date",
    )

    search_fields = (
        "name",
        "creditor",
        "user__username",
    )