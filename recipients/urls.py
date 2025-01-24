from django.urls import path

from recipients.views import home_view, MailingListView, MailingCreateView, MailingUpdateView, MailingDeleteView, \
    MailingDetailView, MessageListView, MessageCreateView, MessageUpdateView, MessageDeleteView, MessageDetailView, \
    RecipientListView, RecipientCreateView, RecipientDeleteView, StartMailingView, MailingStatisticsView

app_name = 'recipients'


urlpatterns = [
    path('home/', home_view, name='home'),
    path('mailing_list/', MailingListView.as_view(), name='mailing_list'),
    path('mailing_form/', MailingCreateView.as_view(), name='mailing_create'),
    path('mailing/<int:pk>/update/', MailingUpdateView.as_view(), name='mailing_update'),
    path('mailings/<int:pk>/delete/', MailingDeleteView.as_view(), name='mailing_delete'),
    path('mailing_detail/<int:pk>/', MailingDetailView.as_view(), name='mailing_detail'),
    path('message_list/', MessageListView.as_view(), name='message_list'),
    path('message_form/', MessageCreateView.as_view(), name='message_create'),
    path('message/<int:pk>/update/', MessageUpdateView.as_view(), name='message_update'),
    path('messages/<int:pk>/delete/', MessageDeleteView.as_view(), name='message_delete'),
    path('message_detail/<int:pk>/', MessageDetailView.as_view(), name='message_detail'),
    path('recipient_list/', RecipientListView.as_view(), name='recipient_list'),
    path('recipient_form/', RecipientCreateView.as_view(), name='recipient_create'),
    path('recipients/<int:pk>/delete/', RecipientDeleteView.as_view(), name='recipient_delete'),
    path('mailing/<int:mailing_id>/start/', StartMailingView.as_view(), name='mailing_start'),
    path('mailing/<int:mailing_id>/statistics', MailingStatisticsView.as_view(), name='mailing_statistics'),
]
