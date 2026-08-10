from django.contrib import admin

from .models import Conversation, ConversationMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "state",
        "pending_type",
        "pending_amount",
        "pending_category",
        "pending_account",
        "updated_at",
    )

    list_filter = (
        "state",
        "pending_type",
    )

    search_fields = (
        "user__username",
    )


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "role",
        "content",
        "created_at",
    )

    list_filter = (
        "role",
        "created_at",
    )

    search_fields = (
        "content",
        "conversation__user__username",
    )