from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.generic.detail import SingleObjectMixin

from recipients.models import Mailing, Recipient, Message
from recipients.tasks import process_mailing


def home_view(request):
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


class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing

    def get_queryset(self):
        if self.request.user.is_manager:
            return Mailing.objects.all()
        else:
            return Mailing.objects.filter(user=self.request.user)


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    fields = ['message', 'recipients']
    success_url = reverse_lazy('recipients:mailing_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['message'].queryset = form.fields['message'].queryset.filter(user=self.request.user).select_related('user')
        form.fields['recipients'].queryset = form.fields['recipients'].queryset.filter(user=self.request.user).select_related('user')
        return form


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    fields = ['first_sending_datetime', 'mailing_end_datetime', 'status', 'message', 'recipients']
    success_url = reverse_lazy('recipients:mailing_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        mailing = self.get_object(request)
        if mailing.status == 'completed':
            messages.error(request, "Эту рассылку нельзя редактировать, так как она завершена.")
            return redirect('recipients:mailing_list')


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    success_url = reverse_lazy('recipients:mailing_list')


class MailingDetailView(LoginRequiredMixin, DetailView):
    model = Mailing

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MessageListView(LoginRequiredMixin, ListView):
    model = Message

    def get_queryset(self):
        if self.request.user.is_manager:
            return Message.objects.all()
        else:
            return Message.objects.filter(user=self.request.user)


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    fields = ['topic', 'body',]
    success_url = reverse_lazy('recipients:message_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    fields = ['topic', 'body',]
    success_url = reverse_lazy('recipients:message_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    success_url = reverse_lazy('recipients:message_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    context_object_name = 'message'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class RecipientListView(LoginRequiredMixin, ListView):
    model = Recipient

    def get_queryset(self):
        if self.request.user.is_manager:
            return Recipient.objects.all()
        else:
            return Recipient.objects.filter(user=self.request.user)


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    fields = ['email', 'full_name', 'comment',]
    success_url = reverse_lazy('recipients:recipient_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class RecipientDeleteView(LoginRequiredMixin, DeleteView):
    model = Recipient
    success_url = reverse_lazy('recipients:recipient_list')

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class StartMailingView(LoginRequiredMixin, SingleObjectMixin, View):
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


class MailingStatisticsView(LoginRequiredMixin, DetailView):
    model = Mailing
    template_name = 'recipients/mailing_statistics.html'
    context_object_name = 'mailing'
    pk_url_kwarg = 'mailing_id'

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
