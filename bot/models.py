from django.contrib.auth.models import User
from django.db import models


class Conversation(models.Model):
    STATES = [
        ("IDLE", "Inactiva"),
        ("WAITING_FOR_ACCOUNT", "Esperando cuenta"),
        ("WAITING_FOR_CATEGORY", "Esperando categoría"),
        ("WAITING_FOR_AMOUNT", "Esperando monto"),
        ("CONFIRMING", "Esperando confirmación"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    state = models.CharField(
        max_length=30,
        choices=STATES,
        default="IDLE",
    )

    pending_type = models.CharField(
        max_length=10,
        blank=True,
    )

    pending_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    pending_category = models.ForeignKey(
        "finance.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_conversations",
    )

    pending_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_conversations",
    )

    pending_transfer_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_transfer_conversations",
    )

    pending_description = models.CharField(
        max_length=255,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.state}"


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=[
            ("USER", "Usuario"),
            ("BOT", "Bot"),
        ],
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"