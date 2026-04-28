from django import views
from django.urls import path
from users.views import SignupView, CustomLoginView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]