# interview/services/twilio_service.py
from twilio.rest import Client
from django.conf import settings

client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH)

def start_call(phone):
    return client.calls.create(
        to=phone,
        from_=settings.TWILIO_NUMBER,
        url="https://meggan-spectacleless-nonreverentially.ngrok-free.dev/voice/"
    )
