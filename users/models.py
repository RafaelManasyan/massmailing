from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    avtr = models.ImageField(verbose_name='Аватар', blank=True)
    email = models.EmailField(unique=True)
    is_manager = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email



