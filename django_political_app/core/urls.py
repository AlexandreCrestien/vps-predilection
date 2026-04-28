from django.urls import path
from .views import AccueilView

urlpatterns = [
    path('home/', AccueilView.as_view(), name='home'),
]