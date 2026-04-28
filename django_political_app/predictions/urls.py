from django.urls import path
from .views import PredictionsView, commune_autocomplete

urlpatterns = [
    path('predictions/', PredictionsView.as_view(), name='predictions'),
    path('api/communes-search/', commune_autocomplete, name='commune-search'),
]