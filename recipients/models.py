from django.db import models


class Recipient(models.Model):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    comment = models.TextField()

    def __str__(self):
        return f'Получатель: {self.full_name}'

    class Meta:
        verbose_name = 'получатель'
        verbose_name_plural = 'получатели'


class Message(models.Model):
    topic = models.CharField(max_length=350)
    body = models.TextField()

    def __str__(self):
        return f'Сообщение: {self.topic}'

    class Meta:
        verbose_name = 'сообщение'
        verbose_name_plural = 'сообщения'


class Mailing(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создано'),
        ('started', 'Запущено'),
        ('completed', 'Завершено')
    ]
    first_sending_datetime = models.DateTimeField()
    mailing_end_datetime = models.DateTimeField()
    status = models.CharField(choices=STATUS_CHOICES, verbose_name='статус', default='created')
    message = models.ForeignKey('Message', verbose_name='Сообщение', on_delete=models.CASCADE)
    recipients = models.ManyToManyField('Recipient', verbose_name='Получатели')

