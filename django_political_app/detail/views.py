from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .services import DetailService
import math

# Create your views here.
class DetailView(LoginRequiredMixin,TemplateView):
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        """ Récupère les détails des communes avec pagination et recherche, puis prépare le contexte pour le template.

        Returns:
            dict: Un dictionnaire contenant les détails des communes, le nombre total, la page actuelle et la limite.
        """
        context = super().get_context_data(**kwargs)
        # Récupère la page depuis l'URL, défaut à 1
        page = int(self.request.GET.get('page', 1))
        limit = int(self.request.GET.get('limit', 25))
        search_query = self.request.GET.get('search', '')
        
        service = DetailService()
        api_response = service.get_detail_communes(page=page, limit=limit, search=search_query)
        total_items = api_response['total']
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
        
        context.update({
            'detail_data': api_response['data'],
            'current_page': page,
            'limit': limit,
            'search_query': search_query,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1,
            'prev_page': page - 1,
            # Liste des options pour le sélecteur d'affichage
            'limit_options': [25, 50, 100]
        })
        return context