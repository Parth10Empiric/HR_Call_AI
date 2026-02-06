from django.urls import path
from .views import voice_interview, call_ui

urlpatterns = [
    path("voice/", voice_interview),
    path("", call_ui, name="call_ui"),
]
