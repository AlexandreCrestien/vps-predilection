from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Votre adresse email',
        widget=forms.EmailInput(attrs={"placeholder": "Votre adresse email"}),
        error_messages={
            "required": "L'adresse email est obligatoire.",
            "invalid": "Entrez une adresse email valide.",
        },
    )

    first_name = forms.CharField(
        label='Prénom',
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Votre prénom"}),
        error_messages={
            "required": "Le prénom est obligatoire.",
        },
    )

    last_name = forms.CharField(
        label='Nom de famille',
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Votre nom de famille"}),
        error_messages={
            "required": "Le nom de famille est obligatoire.",
        },
    )

    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={"placeholder": "Votre mot de passe"}),
        help_text="Votre mot de passe doit contenir au moins 8 caractères.",
        error_messages={
            "required": "Le mot de passe est obligatoire.",
        }
    )

    password2 = forms.CharField(
        label='Confirmez le mot de passe',
        widget=forms.PasswordInput(attrs={"placeholder": "Confirmez votre mot de passe"}),
        help_text="Entrez le même mot de passe que précédemment, pour vérification.",
        error_messages={
            "required": "La confirmation du mot de passe est obligatoire.",
        },
    )
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("email", "first_name", "last_name")
        labels = {
            'email': 'Votre adresse email',
            'first_name': 'Prénom',
            'last_name': 'Nom de famille',
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Votre prénom"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Votre nom de famille"}),
        }

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        required=True,
        label='Votre adresse email',
        widget=forms.EmailInput(attrs={"placeholder": "Entrez votre adresse email"}),
        error_messages={
            "required": "L'adresse email est obligatoire.",
            "invalid": "Entrez une adresse email valide.",
        },
    )
    
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={"placeholder": "Votre mot de passe"}),
    )