from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.generic.detail import SingleObjectMixin

from recipients.models import Mailing, Recipient, Message
from recipients.tasks import process_mailing
from users.models import User


def home_view(request):
    """
    Представление для главной страницы с отображением статистики.
    - Если пользователь авторизован:
    * Менеджеры видят статистику по всем рассылкам и получателям.
    * Обычные пользователи видят только свою статистику.
    - Если пользователь не авторизован, все показатели равны нулю.
    """
    user = request.user

    if user.is_authenticated:
        if user.is_manager:
            total_mailings = Mailing.objects.count()  # Все рассылки
            active_mailings = Mailing.objects.filter(status='started').count()  # Все активные рассылки
            unique_recipients = Recipient.objects.count()  # Все уникальные получатели
        else:
            total_mailings = Mailing.objects.filter(user=user).count()  # Рассылки пользователя
            active_mailings = Mailing.objects.filter(user=user, status='started').count()  # Активные рассылки пользователя
            unique_recipients = Recipient.objects.filter(user=user).count()  # Уникальные получатели пользователя
    else:
        # Для незалогиненных пользователей
        total_mailings = 0
        active_mailings = 0
        unique_recipients = 0

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'unique_recipients': unique_recipients,
    }
    return render(request, 'home.html', context)


@method_decorator(cache_page(60*15), name='dispatch')
class MailingListView(LoginRequiredMixin, ListView):
    """
    Представление для отображения списка рассылок.
    - Кэшируется на 15 минут для оптимизации производительности.
    - Менеджеры видят все рассылки, а обычные пользователи — только свои.
    """
    model = Mailing

    def get_queryset(self):
        if self.request.user.is_manager:
            return Mailing.objects.all()
        return Mailing.objects.filter(user=self.request.user)


class MailingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Представление для создания новых рассылок.
    - Доступно только для пользователей с правом добавления рассылок.
    - Автоматически связывает новую рассылку с текущим пользователем.
    - Ограничивает выбор сообщений и получателей только для текущего пользователя.
    """
    model = Mailing
    fields = ['message', 'recipients']
    success_url = reverse_lazy('recipients:mailing_list')
    permission_required = 'recipients.add_mailing'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['message'].queryset = form.fields['message'].queryset.filter(user=self.request.user).select_related('user')
        form.fields['recipients'].queryset = form.fields['recipients'].queryset.filter(user=self.request.user).select_related('user')
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False  # Указываем, что это не редактирование
        return context


class MailingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Представление для редактирования рассылок. Доступно только пользователю, который создал рассылку. Завершённые
    рассылки редактировать нельзя. Также добавляется контекст, указывающий, что это форма редактирования."""
    model = Mailing
    fields = ['message', 'recipients']
    success_url = reverse_lazy('recipients:mailing_list')
    permission_required = 'recipients.change_mailing'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        mailing = self.get_object()
        if mailing.status == 'completed':
            messages.error(request, "Эту рассылку нельзя редактировать, так как она завершена.")
            return redirect('recipients:mailing_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True  # Указываем, что это редактирование
        return context


class MailingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Mailing
    success_url = reverse_lazy('recipients:mailing_list')
    permission_required = 'recipients.delete_mailing'


class MailingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Представление для отображения деталей конкретной рассылки. Менеджеры могут видеть все рассылки, а пользователи — только свои"""
    model = Mailing
    permission_required = 'recipients.can_view_mailing_detail'

    def get_queryset(self):
        if self.request.user.is_manager:
            return super().get_queryset()
        return super().get_queryset().filter(user=self.request.user)


class MessageListView(LoginRequiredMixin, ListView):
    model = Message

    def get_queryset(self):
        if self.request.user.is_manager:
            return Message.objects.all()
        else:
            return Message.objects.filter(user=self.request.user)


class MessageCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Message
    fields = ['topic', 'body',]
    success_url = reverse_lazy('recipients:message_list')
    permission_required = 'recipients.add_message'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Представление для редактирования сообщений. Пользователи могут редактировать только свои сообщения."""
    model = Message
    fields = ['topic', 'body',]
    success_url = reverse_lazy('recipients:message_list')
    permission_required = 'recipients.change_message'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MessageDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Представление для удаления сообщений. Доступно только пользователям с правом удаления сообщений. Пользователи могут удалять только свои сообщения."""
    model = Message
    success_url = reverse_lazy('recipients:message_list')
    permission_required = 'recipients.delete_message'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MessageDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Представление для просмотра деталей сообщения. Менеджеры видят все сообщения, а пользователи — только свои."""
    model = Message
    context_object_name = 'message'
    permission_required = 'recipients.view_message'

    def get_queryset(self):
        if self.request.user.is_manager:
            return super().get_queryset()
        return super().get_queryset().filter(user=self.request.user)


class RecipientListView(LoginRequiredMixin, ListView):
    """Представление для отображения списка клиентов. Менеджеры видят всех клиентов, а пользователи — только своих."""
    model = Recipient

    def get_queryset(self):
        if self.request.user.is_manager:
            return Recipient.objects.all()
        else:
            return Recipient.objects.filter(user=self.request.user)


class RecipientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """“Представление для создания новых клиентов. Автоматически связывает клиента с текущим пользователем. Доступно только для пользователей с правом добавления клиентов.”"""
    model = Recipient
    fields = ['email', 'full_name', 'comment',]
    success_url = reverse_lazy('recipients:recipient_list')
    permission_required = 'recipients.add_recipient'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class RecipientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Представление для удаления клиентов. Пользователи могут удалять только своих клиентов. Доступно только с соответствующими правами."""
    model = Recipient
    success_url = reverse_lazy('recipients:recipient_list')
    permission_required = 'recipients.delete_recipient'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class StartMailingView(LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View):
    """Представление для запуска рассылок. Доступно только для незавершённых рассылок. Обновляет статус рассылки на ‘запущена’ и обрабатывает её."""
    model = Mailing
    success_url = reverse_lazy('recipients:mailing_list')  # Переход после завершения
    pk_url_kwarg = 'mailing_id'

    def post(self, request, *args, **kwargs):
        mailing = self.get_object()

        # Ограничение для завершённых рассылок
        if mailing.status == 'completed':
            messages.error(request, "Нельзя запустить завершённую рассылку.")
            return redirect(self.success_url)

        # Проверка статуса перед запуском
        if mailing.status == 'created':
            mailing.status = 'started'
            mailing.first_sending_datetime = now()
            mailing.save()

            try:
                process_mailing(mailing.id)
                messages.success(request, f"Рассылка '{mailing.id}' успешно запущена!")
            except Exception as e:
                messages.error(request, f"Ошибка при запуске рассылки: {str(e)}")
        else:
            messages.warning(request, "Рассылка уже была запущена или завершена.")

        return redirect('recipients:mailing_detail', mailing.id)


class MailingStatisticsView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Представление для отображения статистики рассылки. Доступно менеджерам для всех рассылок и пользователям для
    их собственных. Показывает успешные, неуспешные и общее количество попыток отправки."""
    model = Mailing
    template_name = 'recipients/mailing_statistics.html'
    context_object_name = 'mailing'
    pk_url_kwarg = 'mailing_id'
    permission_required = 'recipients.can_view_mailing_statistics'

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_manager:
            return queryset.filter(user=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mailing = self.get_object()
        # Добавляем данные для статистики
        context['successful_attempts'] = mailing.mailingattempt_set.filter(attempt_status='successful').count()
        context['unsuccessful_attempts'] = mailing.mailingattempt_set.filter(attempt_status='unsuccessful').count()
        context['total_attempts'] = mailing.mailingattempt_set.count()
        return context


@method_decorator(cache_page(60*15), name='dispatch')
class ManagerUserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Представление для отображения списка пользователей сервиса.
    - Кэширует данные на 15 минут для оптимизации.
    - Доступно только для авторизованных пользователей с правом 'users.can_view_user'.
    - Исключает менеджеров и суперпользователей из списка.
    """
    model = User
    template_name = 'recipients/manager_user_list.html'
    context_object_name = 'users'
    permission_required = 'users.can_view_user'

    def get_queryset(self):
        return User.objects.filter(is_manager=False, is_superuser=False)


class ToggleUserStatusView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Представление для изменения статуса пользователя (активация/деактивация).
    - Используется для блокировки и разблокировки пользователей.
    - Доступно только для авторизованных пользователей с правом 'users.can_change_user'.
    - Исключает возможность блокировки менеджеров и суперпользователей.
    """
    model = User
    fields = []  # Поле пустое, так как изменение выполняется программно
    template_name = 'recipients/toggle_user_status.html'
    permission_required = 'users.can_change_user'
    success_url = reverse_lazy('recipients:manager_user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = self.kwargs.get('action')  # Передаём `action` в контекст
        return context

    def form_valid(self, form):
        user = form.instance
        action = self.kwargs.get('action')  # Получаем действие (block/unblock) из URL
        if action == 'block':
            if user.is_manager or user.is_superuser:
                messages.error(self.request, "Невозможно заблокировать администратора.")
                return redirect(self.success_url)
            user.is_active = False
            messages.success(self.request, f"Пользователь {user.get_full_name()} заблокирован.")
        elif action == 'unblock':
            user.is_active = True
            messages.success(self.request, f"Пользователь {user.get_full_name()} разблокирован.")
        user.save()
        return super().form_valid(form)


class CompleteMailingView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Представление для завершения рассылки (изменение статуса на 'completed').
    - Доступно только для авторизованных пользователей с правом 'recipients.change_mailing'.
    - Меняет статус рассылки на завершённый, если она ещё не завершена.
    - Выводит соответствующее сообщение пользователю в зависимости от результата операции.
    """
    model = Mailing
    permission_required = 'recipients.change_mailing'

    def post(self, request, mailing_id, *args, **kwargs):
        mailing = get_object_or_404(Mailing, id=mailing_id)

        # Меняем статус на завершённый
        if mailing.status != 'completed':
            mailing.status = 'completed'
            mailing.save()
            messages.success(request, f"Рассылка '{mailing.id}' завершена.")
        else:
            messages.warning(request, f"Рассылка '{mailing.id}' уже завершена.")

        return redirect('recipients:mailing_list')
