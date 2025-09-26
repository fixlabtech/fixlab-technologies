from django.urls import path
from .views import RegistrationAPIView, CheckUserAPIView,VerifyAndRegisterAPIView,HealthCheckView


urlpatterns = [
    path('registrations/', RegistrationAPIView.as_view(), name='registrations-api'),
    path("check-user", CheckUserAPIView.as_view(), name="check-user"),
    path("verify-register/", VerifyAndRegisterAPIView.as_view(), name="verify-register"),
    path('health/', HealthCheckView.as_view(), name='health-check'),

    

]
