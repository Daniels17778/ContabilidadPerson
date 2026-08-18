from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from finance.models import Account, Category
from bot.parser import parse_message, parse_amount, detect_category
from bot.services import chat


class ParserAmountTests(TestCase):

    def test_numero_simple(self):
        self.assertEqual(parse_amount("15000"), Decimal("15000"))

    def test_formato_puntos(self):
        self.assertEqual(parse_amount("$15.000"), Decimal("15000"))

    def test_formato_comas(self):
        self.assertEqual(parse_amount("15,000"), Decimal("15000"))

    def test_mil(self):
        self.assertEqual(parse_amount("15 mil"), Decimal("15000"))

    def test_k(self):
        self.assertEqual(parse_amount("15k"), Decimal("15000"))

    def test_millon(self):
        self.assertEqual(parse_amount("1.5 millones"), Decimal("1500000"))


class ParserCategoryTests(TestCase):

    def test_categoria_con_tilde(self):
        self.assertEqual(detect_category("compré medicina"), "salud")

    def test_categoria_sin_tilde(self):
        self.assertEqual(detect_category("compre medicina"), "salud")

    def test_pago_no_es_categoria_salario(self):
        # 'pago' por sí solo ya no debe clasificar como salario
        self.assertEqual(
            detect_category("hice un pago de arriendo"),
            "arriendo",
        )

    def test_sin_categoria_reconocida(self):
        self.assertIsNone(detect_category("xyz cosa random 123"))


class ParserMessageTypeTests(TestCase):

    def test_gasto_completo(self):
        result = parse_message("gasté 15000 en comida")
        self.assertEqual(result["type"], "EXPENSE")
        self.assertEqual(result["amount"], Decimal("15000"))
        self.assertEqual(result["category"], "alimentación")

    def test_ingreso_completo(self):
        result = parse_message("recibí 1.500.000 de salario")
        self.assertEqual(result["type"], "INCOME")
        self.assertEqual(result["amount"], Decimal("1500000"))

    def test_transferencia_con_cuentas(self):
        result = parse_message("pasé 50 mil de Bancolombia a Nequi")
        self.assertEqual(result["type"], "TRANSFER")
        self.assertEqual(result["source_account"], "bancolombia")
        self.assertEqual(result["destination_account"], "nequi")

    def test_consulta_de_saldo(self):
        result = parse_message("cuánto tengo")
        self.assertEqual(result["type"], "BALANCE")

    def test_consulta_por_categoria(self):
        result = parse_message("cuánto gasté en comida este mes")
        self.assertEqual(result["type"], "CATEGORY_TOTAL")
        self.assertEqual(result["category"], "alimentación")
        self.assertEqual(result["period"], "MONTH")


class ChatTransferFlowTests(TestCase):
    """
    Prueba de regresión del bug de transferencias por pasos:
    antes de la corrección, esto lanzaba AttributeError en el
    paso donde se pide la cuenta destino.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test1234",
        )

        self.bancolombia = Account.objects.create(
            user=self.user,
            name="Bancolombia",
            account_type="BANK",
            balance=Decimal("1000000"),
        )

        self.nequi = Account.objects.create(
            user=self.user,
            name="Nequi",
            account_type="NEQUI",
            balance=Decimal("0"),
        )

    def test_transferencia_paso_a_paso_no_rompe(self):
        response = chat(self.user, "quiero transferir plata")
        self.assertIn("monto", response.lower())

        response = chat(self.user, "50 mil")
        self.assertIn("cuenta sale", response.lower())

        # Este era el paso que antes crasheaba con AttributeError
        response = chat(self.user, "Bancolombia")
        self.assertIn("a qué cuenta", response.lower())

        response = chat(self.user, "Nequi")
        self.assertIn("confirmas", response.lower())

        response = chat(self.user, "si")
        self.assertIn("realizada", response.lower())

        self.bancolombia.refresh_from_db()
        self.nequi.refresh_from_db()

        self.assertEqual(self.bancolombia.balance, Decimal("950000"))
        self.assertEqual(self.nequi.balance, Decimal("50000"))

    def test_transferencia_no_permite_misma_cuenta_origen_destino(self):
        chat(self.user, "quiero transferir plata")
        chat(self.user, "50 mil")
        chat(self.user, "Bancolombia")

        # Intenta poner la misma cuenta como destino
        response = chat(self.user, "Bancolombia")
        self.assertIn("deben ser diferentes", response)

        # Y luego sí debe aceptar una cuenta distinta
        response = chat(self.user, "Nequi")
        self.assertIn("confirmas", response.lower())


class ChatExpenseFlowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser2",
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
            name="alimentación",
            type="EXPENSE",
        )

    def test_gasto_directo_completo(self):
        response = chat(
            self.user,
            "gasté 15000 en comida en Efectivo",
        )
        self.assertIn("confirmas", response.lower())

        response = chat(self.user, "si")
        self.assertIn("registrado", response.lower())

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("85000"))