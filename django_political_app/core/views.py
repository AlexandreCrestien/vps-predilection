from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic.base import View

# Create your views here.
class AccueilView(TemplateView):
    template_name = 'home.html'
