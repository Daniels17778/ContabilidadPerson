from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from finance.models import Account, Category
from finance.services import (
    register_expense,
    register_income,
    transfer_money,
)


class RegisterExpenseTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234",
        )

        self.account = Account.objects.create(
            user=self.user,
            name="Efectivo",
            account_type="CASH",
            balance=Decimal("100000"),
        )

        self.category = Category.objects.create(
            user=self.user,
            name="Comida",
            type="EXPENSE",
        )

    def test_registra_gasto_y_descuenta_saldo(self):
        register_expense(
            user=self.user,
            account=self.account,
            category=self.category,
            amount=Decimal("30000"),
        )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("70000"))

    def test_rechaza_saldo_insuficiente(self):
        with self.assertRaises(ValueError):
            register_expense(
                user=self.user,
                account=self.account,
                category=self.category,
                amount=Decimal("999999"),
            )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("100000"))

    def test_rechaza_categoria_de_ingreso(self):
        income_category = Category.objects.create(
            user=self.user,
            name="Salario",
            type="INCOME",
        )

        with self.assertRaises(ValueError):
            register_expense(
                user=self.user,
                account=self.account,
                category=income_category,
                amount=Decimal("10000"),
            )

    def test_rechaza_cuenta_de_otro_usuario(self):
        other_user = User.objects.create_user(
            username="otro",
            password="test1234",
        )

        other_account = Account.objects.create(
            user=other_user,
            name="Cuenta ajena",
            account_type="CASH",
            balance=Decimal("50000"),
        )

        with self.assertRaises(ValueError):
            register_expense(
                user=self.user,
                account=other_account,
                category=self.category,
                amount=Decimal("10000"),
            )

    def test_rechaza_monto_negativo_o_cero(self):
        with self.assertRaises(ValueError):
            register_expense(
                user=self.user,
                account=self.account,
                category=self.category,
                amount=Decimal("0"),
            )


class RegisterIncomeTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234",
        )

        self.account = Account.objects.create(
            user=self.user,
            name="Efectivo",
            account_type="CASH",
            balance=Decimal("0"),
        )

        self.category = Category.objects.create(
            user=self.user,
            name="Salario",
            type="INCOME",
        )

    def test_registra_ingreso_y_aumenta_saldo(self):
        register_income(
            user=self.user,
            account=self.account,
            category=self.category,
            amount=Decimal("500000"),
        )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("500000"))


class TransferMoneyTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234",
        )

        self.source = Account.objects.create(
            user=self.user,
            name="Bancolombia",
            account_type="BANK",
            balance=Decimal("100000"),
        )

        self.destination = Account.objects.create(
            user=self.user,
            name="Nequi",
            account_type="NEQUI",
            balance=Decimal("0"),
        )

    def test_transfiere_correctamente(self):
        transfer_money(
            user=self.user,
            source_account=self.source,
            destination_account=self.destination,
            amount=Decimal("40000"),
        )

        self.source.refresh_from_db()
        self.destination.refresh_from_db()

        self.assertEqual(self.source.balance, Decimal("60000"))
        self.assertEqual(self.destination.balance, Decimal("40000"))

    def test_rechaza_transferir_a_la_misma_cuenta(self):
        with self.assertRaises(ValueError):
            transfer_money(
                user=self.user,
                source_account=self.source,
                destination_account=self.source,
                amount=Decimal("1000"),
            )

    def test_rechaza_saldo_insuficiente(self):
        with self.assertRaises(ValueError):
            transfer_money(
                user=self.user,
                source_account=self.source,
                destination_account=self.destination,
                amount=Decimal("999999"),
            )

        self.source.refresh_from_db()
        self.destination.refresh_from_db()
        self.assertEqual(self.source.balance, Decimal("100000"))
        self.assertEqual(self.destination.balance, Decimal("0"))