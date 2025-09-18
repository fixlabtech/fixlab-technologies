from django.urls import path
from .views import RegistrationAPIView, CheckUserAPIView,VerifyAndRegisterAPIView

urlpatterns = [
    path('registrations/', RegistrationAPIView.as_view(), name='registrations-api'),
    path("check-user", CheckUserAPIView.as_view(), name="check-user"),
    path("api/verify-register/", VerifyAndRegisterAPIView.as_view(), name="verify-register"),

    

]
