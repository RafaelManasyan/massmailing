from django.contrib import admin

from users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'avtr', 'email', 'is_manager')
    search_fields = ('email',)  # Поиск по email
    list_filter = ('is_manager',)  # Фильтр по статусу менеджера
    readonly_fields = ('id', 'email')  # Поля, которые нельзя редактировать
