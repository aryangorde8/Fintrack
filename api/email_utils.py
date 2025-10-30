from django.core.mail import send_mail
from django.conf import settings

def send_email_alert(user_email, subject, message):
    """Send email alert"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
