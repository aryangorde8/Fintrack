from django.conf import settings
from twilio.rest import Client

def send_sms_alert(user_phone, message):
    """Send SMS alert using Twilio"""
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=user_phone
        )
        
        return True, message.sid
    except Exception as e:
        return False, str(e)
