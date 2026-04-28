from django.urls import path
from .views import DetailView



urlpatterns = [
    path('detail/', DetailView.as_view(), name='detail'),
]