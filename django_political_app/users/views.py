from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic.base import View

from django.views import View
from django.shortcuts import render, redirect
from .forms import SignupForm, LoginForm
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth import login

class SignupView(View):
    def dispatch(self, request, *args, **kwargs):
        """ Dispatch la requête en fonction de l'état de l'utilisateur.

        Args:
            request (_type_): vérification de l'état de l'utilisateur

        Returns:
            _type_: redirection vers la page d'accueil si l'utilisateur est déjà connecté, sinon continue le processus normal de dispatch.
        """
        if request.user.is_authenticated:
            return redirect("/home")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """ Affiche le formulaire d'inscription.

        Args:
            request (_type_): Requête GET pour afficher le formulaire d'inscription.

        Returns:
            _type_: Rendu de la page d'inscription avec le formulaire.
        """
        return render(request, "signup.html", {"form": SignupForm()})

    def post(self, request):
        """ Traite le formulaire d'inscription soumis.

        Args:
            request (_type_): Requête POST pour soumettre le formulaire d'inscription.

        Returns:
            _type_: Rendu de la page d'inscription avec le formulaire. Si le formulaire est valide, redirection vers la page d'accueil avec un message de succès.
        """
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.email
            user.save()
            login(request, user)
            messages.success(request, "Inscription réussie. Vous êtes maintenant connecté.")
            return redirect("/home")
        return render(request, "signup.html", {"form": form})

class CustomLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        """ Détermine l'URL de redirection après une connexion réussie.

        Returns:
            str: URL de redirection vers la page d'accueil.
        """
        return "/home"
    
    def form_valid(self, form):
        """ Affiche un message de succès ou d'erreur en fonction du résultat de la validation du formulaire de connexion.

        Args:
            form (_type_): Formulaire de connexion soumis par l'utilisateur.

        Returns:
            bool: Résultat de la validation du formulaire. Si la validation est réussie, affiche un message de succès, sinon affiche un message d'erreur.
        """
        is_valid = super().form_valid(form)
        if is_valid:
            messages.success(self.request, "Vous êtes maintenant connecté.")
        else:
            messages.error(self.request, "Échec de la connexion. Veuillez vérifier vos identifiants.")
        return is_valid
    
    def dispatch(self, request, *args, **kwargs):
        """Redirige les utilisateurs déjà authentifiés vers la page d'accueil.

        Args:
            request (_type_): Requête GET pour afficher le formulaire de connexion.

        Returns:
            _type_: Rendu de la page de connexion avec le formulaire. Si l'utilisateur est déjà connecté, redirection vers la page d'accueil.
        """
        if request.user.is_authenticated:
            return redirect("/home")

        return super().dispatch(request, *args, **kwargs)