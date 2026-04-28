import pytest
from django.test import Client
from django.urls import reverse
from django.db import IntegrityError
from users.models import CustomUser
from users.forms import SignupForm, LoginForm


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="test@example.com",
        email="test@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def authenticated_client(client, user):
    client.login(username="test@example.com", password="StrongPass123!")
    return client


# ============================================================
# MODELS
# ============================================================

@pytest.mark.django_db
class TestCustomUserModel:

    def test_creation_utilisateur(self):
        user = CustomUser.objects.create_user(
            username="alice@example.com",
            email="alice@example.com",
            password="Pass1234!",
        )
        assert user.pk is not None
        assert user.email == "alice@example.com"

    def test_email_unique(self, user):
        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(
                username="autre",
                email="test@example.com",
                password="AutrePass!",
            )

    def test_username_est_email(self, user):
        assert user.username == user.email

    def test_mot_de_passe_est_hache(self):
        user = CustomUser.objects.create_user(
            username="bob@example.com",
            email="bob@example.com",
            password="MonMotDePasse!",
        )
        assert user.password != "MonMotDePasse!"
        assert user.check_password("MonMotDePasse!")

    def test_utilisateur_actif_par_defaut(self):
        user = CustomUser.objects.create_user(
            username="carol@example.com",
            email="carol@example.com",
            password="Pass!",
        )
        assert user.is_active is True

    def test_utilisateur_non_staff_par_defaut(self):
        user = CustomUser.objects.create_user(
            username="dave@example.com",
            email="dave@example.com",
            password="Pass!",
        )
        assert user.is_staff is False


# ============================================================
# VIEWS — SIGNUP
# ============================================================

@pytest.mark.django_db
class TestSignupView:

    def test_get_affiche_formulaire(self, client):
        response = client.get(reverse("signup"))
        assert response.status_code == 200
        assert "form" in response.context

    def test_inscription_valide_cree_utilisateur(self, client):
        data = {
            "email": "nouveau@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        client.post(reverse("signup"), data=data)
        assert CustomUser.objects.filter(email="nouveau@example.com").exists()

    def test_inscription_valide_redirige_vers_home(self, client):
        data = {
            "email": "nouveau@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("signup"), data=data)
        assert response.status_code == 302
        assert response["Location"] == "/home"

    def test_inscription_valide_connecte_utilisateur(self, client):
        data = {
            "email": "nouveau@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        client.post(reverse("signup"), data=data)
        response = client.get(reverse("signup"))
        assert response.status_code == 302

    def test_inscription_email_invalide(self, client):
        data = {
            "email": "pas-un-email",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("signup"), data=data)
        assert response.status_code == 200
        assert not CustomUser.objects.filter(email="pas-un-email").exists()

    def test_inscription_mots_de_passe_differents(self, client):
        data = {
            "email": "test2@example.com",
            "password1": "StrongPass123!",
            "password2": "AutrePass456!",
        }
        response = client.post(reverse("signup"), data=data)
        assert response.status_code == 200
        assert not CustomUser.objects.filter(email="test2@example.com").exists()

    def test_inscription_email_deja_utilise(self, client, user):
        data = {
            "email": user.email,
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        response = client.post(reverse("signup"), data=data)
        assert response.status_code == 200

    def test_utilisateur_connecte_redirige(self, authenticated_client):
        response = authenticated_client.get(reverse("signup"))
        assert response.status_code == 302
        assert response["Location"] == "/home"


# ============================================================
# VIEWS — LOGIN
# ============================================================

@pytest.mark.django_db
class TestCustomLoginView:

    def test_get_affiche_formulaire(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_connexion_valide_redirige_vers_home(self, client, user):
        data = {
            "username": user.email,
            "password": "StrongPass123!",
        }
        response = client.post(reverse("login"), data=data)
        assert response.status_code == 302
        assert response["Location"] == "/home"

    def test_connexion_mauvais_mot_de_passe(self, client, user):
        data = {
            "username": user.email,
            "password": "mauvais_mdp",
        }
        response = client.post(reverse("login"), data=data)
        assert response.status_code == 200

    def test_connexion_email_inexistant(self, client):
        data = {
            "username": "inconnu@example.com",
            "password": "Pass123!",
        }
        response = client.post(reverse("login"), data=data)
        assert response.status_code == 200

    def test_utilisateur_connecte_redirige(self, authenticated_client):
        response = authenticated_client.get(reverse("login"))
        assert response.status_code == 302
        assert response["Location"] == "/home"


# ============================================================
# VIEWS — LOGOUT
# ============================================================

@pytest.mark.django_db
class TestLogoutView:

    def test_logout_deconnecte_utilisateur(self, authenticated_client):
        response = authenticated_client.post(reverse("logout"))
        assert response.status_code == 302


# ============================================================
# FORMS — SIGNUP
# ============================================================

@pytest.mark.django_db
class TestSignupForm:

    def test_form_valide(self):
        data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignupForm(data=data)
        assert form.is_valid()

    def test_email_manquant(self):
        data = {
            "email": "",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "email" in form.errors

    def test_email_invalide(self):
        data = {
            "email": "pas-un-email",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "email" in form.errors

    def test_prenom_manquant(self):
        data = {
            "email": "alice@example.com",
            "first_name": "",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "first_name" in form.errors

    def test_nom_manquant(self):
        data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "last_name" in form.errors

    def test_mots_de_passe_differents(self):
        data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "StrongPass123!",
            "password2": "AutrePass456!",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "password2" in form.errors

    def test_mot_de_passe_trop_court(self):
        data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "abc",
            "password2": "abc",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "password2" in form.errors

    def test_mot_de_passe_manquant(self):
        data = {
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Dupont",
            "password1": "",
            "password2": "",
        }
        form = SignupForm(data=data)
        assert not form.is_valid()
        assert "password1" in form.errors


# ============================================================
# FORMS — LOGIN
# ============================================================

class TestLoginForm:

    def test_form_vide_invalide(self):
        form = LoginForm(data={})
        assert not form.is_valid()
        assert "username" in form.errors

    def test_email_invalide(self):
        data = {
            "username": "pas-un-email",
            "password": "StrongPass123!",
        }
        form = LoginForm(data=data)
        assert not form.is_valid()
        assert "username" in form.errors

    def test_email_manquant(self):
        data = {
            "username": "",
            "password": "StrongPass123!",
        }
        form = LoginForm(data=data)
        assert not form.is_valid()
        assert "username" in form.errors

    def test_mot_de_passe_manquant(self):
        data = {
            "username": "alice@example.com",
            "password": "",
        }
        form = LoginForm(data=data)
        assert not form.is_valid()
        assert "password" in form.errors