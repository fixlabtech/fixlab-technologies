from django.urls import path
from .views import RegistrationAPIView, CheckUserAPIView,HealthCheckView


urlpatterns = [
    path('registrations/', RegistrationAPIView.as_view(), name='registrations-api'),
    path("check-user", CheckUserAPIView.as_view(), name="check-user"),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
