import folium
from django.views.generic import TemplateView
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from .services import GeoService

class MapView(LoginRequiredMixin, TemplateView):
    template_name = 'map.html'

    def get_city_color(self, stats):
        """ Détermine la couleur d'une commune en fonction de ses résultats électoraux.

        Args:
            stats (dict): Un dictionnaire contenant les résultats électoraux de la commune.

        Returns:
            str: La couleur à utiliser pour le polygone de la commune.
        """
        if not stats:
            return "#bdc3c7" # Gris si aucune donnée
        
        g = stats.get('pct_gauche', 0)
        c = stats.get('pct_centre', 0)
        d = stats.get('pct_droite', 0)

        if g > c and g > d: return "#e74c3c" # Rouge
        if c > g and c > d: return "#f1c40f" # Jaune/Orange
        if d > g and d > c: return "#3498db" # Bleu
        return "#95a5a6"

    def get_context_data(self, **kwargs):
        """ Prépare le contexte pour la vue de la carte, incluant les données géographiques et électorales nécessaires pour afficher la carte interactive.
    
        Returns:            
            dict: Un dictionnaire contenant les données nécessaires pour rendre la carte dans le template.
        """
        context = super().get_context_data(**kwargs)
        service = GeoService()

        # 1. Récupération des paramètres de l'URL
        # On récupère 'department' (défaut 59) et 'year' (défaut 2022)
        dept_code = self.request.GET.get('department', '59')
        year = self.request.GET.get('year', '2022')

        # 2. Gestion des départements (Cache long : 24h)
        departments = cache.get('all_departments')
        if not departments:
            departments = service.get_all_departments()
            cache.set('all_departments', departments, timeout=86400)

        # 2. Code département
        dept_code = self.request.GET.get('department', '59')
        
        # 3. DONNÉES DE LA CARTE (Cache moyen : 2h)
        # On inclut l'année dans la clé pour séparer les résultats 2012, 2017 et 2022
        cache_key = f'full_map_data_{dept_code}_{year}'
        data = cache.get(cache_key)
        if not data:
            data = service.get_full_map_data(dept_code, year=year)
            cache.set(cache_key, data, timeout=7200)

        if data:
            # Création de la carte Folium (Logique inchangée)
            m = folium.Map(
                location=data['center'], 
                zoom_start=9, 
                tiles="Cartodb dark_matter"
            )

            for commune in data['communes']:
                if commune['contour']:
                    stats = commune['stats']
                    color = self.get_city_color(stats)
                    
                    # Préparation du texte du Popup
                    popup_content = f"""
                        <strong>{commune['nom']} ({commune['code_insee']})</strong><br/>
                        Gauche : {stats.get('pct_gauche', 'N/A')}%<br/>
                        Centre : {stats.get('pct_centre', 'N/A')}%<br/>
                        Droite : {stats.get('pct_droite', 'N/A')}%<br/>
                        Abstention : {stats.get('statistics', {}).get('% Abs/Ins', 'N/A')}%
                    """

                    folium.GeoJson(
                        commune['contour'],
                        name=commune['nom'],
                        style_function=lambda x, color=color: {
                            'fillColor': color,
                            'color': 'white',
                            'weight': 0.5,
                            'fillOpacity': 0.7,
                        },
                        highlight_function=lambda x: {
                            'weight': 2,
                            'color': 'black',
                            'fillOpacity': 0.9
                        },
                        tooltip=commune['nom'],
                        popup=folium.Popup(popup_content, max_width=250)
                    ).add_to(m)

            # Marqueur Préfecture
            folium.Marker(
                location=data['center'],
                popup=f"Préfecture : {data['dept_nom']}",
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)

            # Mise à jour du contexte pour le template HTML
            context.update({
                'map': m._repr_html_(),
                'dept_nom': data['dept_nom'],
                'current_dept': dept_code,
                'current_year': year, # Très important pour colorer le bon bouton
                'departments': departments,
            })
        
        return context