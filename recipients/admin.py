from django.contrib import admin
from .models import Recipient, Message, Mailing, MailingAttempt


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'full_name', 'comment')
    search_fields = ('email', 'full_name')
    list_filter = ('email',)
    ordering = ('email',)
    fieldsets = (
        (None, {
            'fields': ('email', 'full_name', 'comment', 'user'),
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'body')
    search_fields = ('topic',)
    ordering = ('topic',)


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_sending_datetime', 'mailing_end_datetime', 'status', 'message_display', 'recipients_count')
    search_fields = ('status',)
    list_filter = ('status', 'first_sending_datetime')
    ordering = ('-first_sending_datetime',)
    filter_horizontal = ('recipients',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('first_sending_datetime', 'mailing_end_datetime', 'status'),
        }),
        ('Связи', {
            'fields': ('message', 'recipients', 'user'),
        }),
    )

    @admin.display(description='Сообщение')
    def message_display(self, obj):
        return obj.message.topic

    @admin.display(description='Количество получателей')
    def recipients_count(self, obj):
        return obj.recipients.count()


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    exclude = ('attempt_datetime',)  # Исключаем поле из формы
    list_display = ('attempt_status', 'mailing', 'recipient', 'attempt_datetime', 'mail_reply')
    list_filter = ('attempt_status', 'attempt_datetime')
