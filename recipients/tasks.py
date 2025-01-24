from django.core.mail import send_mail
from .models import Mailing, MailingAttempt
from config.settings import EMAIL_HOST_USER
from django.utils.timezone import now


def process_mailing(mailing_id):
    """
    Обрабатывает отправку сообщений для конкретной рассылки.
    """
    try:
        # Получаем рассылку
        mailing = Mailing.objects.get(id=mailing_id)
        recipients = mailing.recipients.all()

        if mailing.first_sending_datetime is None:
            mailing.first_sending_datetime = now()

        for recipient in recipients:
            try:
                # Отправка письма
                send_mail(
                    subject=mailing.message.topic,
                    message=mailing.message.body,
                    from_email=EMAIL_HOST_USER,
                    recipient_list=[recipient.email],
                )

                MailingAttempt.objects.create(
                    attempt_datetime=now(),
                    attempt_status='successful',
                    mail_reply='Успешно отправлено',
                    mailing=mailing,
                    recipient=recipient,
                )

            except Exception as e:
                MailingAttempt.objects.create(
                    attempt_datetime=now(),
                    attempt_status='unsuccessful',
                    mail_reply=str(e),
                    mailing=mailing,
                    recipient=recipient,
                )

        # Обновление статуса рассылки
        mailing.status = 'completed'
        mailing.mailing_end_datetime = now()
        mailing.save()

    except Mailing.DoesNotExist:
        raise ValueError(f"Рассылка с ID {mailing_id} не найдена.")
    except Exception as e:
        print(e)