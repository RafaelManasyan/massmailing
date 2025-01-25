from django.conf import settings
from django.db import models


class Recipient(models.Model):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    comment = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_recipients',
                             verbose_name='Владелец', null=True)

    def __str__(self):
        return f'Получатель: {self.full_name}'

    class Meta:
        verbose_name = 'получатель'
        verbose_name_plural = 'получатели'
        permissions = [
            ('can_view_all_recipients', 'Может просматривать всех получателей')
        ]


class Message(models.Model):
    topic = models.CharField(max_length=350)
    body = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_messages',
                             verbose_name='Владелец', null=True)

    def __str__(self):
        return f'Сообщение: {self.topic}'

    class Meta:
        verbose_name = 'сообщение'
        verbose_name_plural = 'сообщения'
        permissions = [
            ('can_view_all_messages', 'Может просматривать все сообщения')
        ]


class Mailing(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создано'),
        ('started', 'Запущено'),
        ('completed', 'Завершено')
    ]
    first_sending_datetime = models.DateTimeField(null=True, blank=True)
    mailing_end_datetime = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, verbose_name='статус', default='created')
    message = models.ForeignKey('Message', verbose_name='Сообщение', on_delete=models.CASCADE)
    recipients = models.ManyToManyField('Recipient', verbose_name='Получатели')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_mailings',
                             verbose_name='Владелец', null=True)

    def __str__(self):
        return f"Рассылка: {self.status}"

    class Meta:
        verbose_name = 'рассылка'
        verbose_name_plural = 'рассылки'
        ordering = ['-first_sending_datetime']
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_view_mailing_statistics', 'Может просматривать статистику рассылки'),
        ]


class MailingAttempt(models.Model):
    STATUS_CHOICES = [
        ('successful', 'Успешно'),
        ('unsuccessful', 'Неуспешно'),
    ]
    attempt_datetime = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время попытки')
    attempt_status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')
    mail_reply = models.TextField(blank=True, null=True, verbose_name='Ответ почтового сервера')
    mailing = models.ForeignKey('Mailing', on_delete=models.CASCADE, verbose_name='Рассылка')
    recipient = models.ForeignKey('Recipient', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Получатель')  # Новый столбец

    def __str__(self):
        return f"Попытка: {self.attempt_status} для {self.recipient.email}"

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылки'
        permissions = [
            ('can_view_all_attempts', 'Может просматривать все попытки рассылок'),
        ]