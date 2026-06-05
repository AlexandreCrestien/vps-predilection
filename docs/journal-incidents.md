# Journal d'incidents et de décisions

## Choix techniques

| Choix | Raison |
|---|---|
| VPS OVH Ubuntu | Fourni dans le cadre du projet |
| Docker + Docker Compose | Déploiement reproductible et isolé |
| Traefik comme reverse proxy | Intégration native Docker, HTTPS automatique via Let's Encrypt |
| DuckDNS | Nom de domaine gratuit pour activer le HTTPS |
| GitHub Container Registry (ghcr.io) | Intégré à GitHub, pas de service tiers supplémentaire |
| `docker/metadata-action` + `docker/build-push-action` | Actions officielles Docker recommandées par la doc GitHub |
| Déploiement uniquement sur release | Évite les déploiements non intentionnels sur chaque push |
| Tags dynamiques (`develop`, `v1.x`) | Versionning clair — `develop` pour les tests, `vX.X` pour la prod |

---

## Incidents rencontrés

### 1. iptables bloquait `apt update`

**Problème** : Après avoir configuré le pare-feu, `apt update` échouait avec une erreur de résolution DNS.  
**Diagnostic** : La règle `DROP` bloquait les réponses aux connexions sortantes.  
**Solution** : Ajout de la règle `ESTABLISHED,RELATED` avant le DROP.

```bash
sudo iptables -I INPUT 1 -m state --state ESTABLISHED,RELATED -j ACCEPT
```

---

### 2. Django `DisallowedHost`

**Problème** : Django retournait une erreur 400 lors de l'accès via le domaine.  
**Diagnostic** : Le domaine n'était pas dans `ALLOWED_HOSTS`.  
**Solution** : Ajout du domaine dans `settings.py`.

```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'predilection.duckdns.org']
CSRF_TRUSTED_ORIGINS = ['https://predilection.duckdns.org']
```

---

### 3. `docker compose pull` refusé sur le VPS

**Problème** : `permission denied while trying to connect to the Docker API`.  
**Diagnostic** : L'utilisateur `ubuntu` n'était pas dans le groupe `docker`.  
**Solution** :

```bash
sudo usermod -aG docker ubuntu
sudo reboot
```

---

### 4. Images non mises à jour sur le VPS

**Problème** : Après un push, le VPS continuait à utiliser l'ancienne image.  
**Diagnostic** : Le tag `v1.0` était fixe — Docker ne sait pas qu'une image avec le même tag a changé.  
**Solution** : Utilisation de `docker/metadata-action` pour générer des tags dynamiques (`develop`, `v1.x`) et ajout d'un `sed` dans le script de déploiement pour remplacer le tag au moment de la release.

---

### 5. Authentification SSH par mot de passe toujours active

**Problème** : Malgré `PasswordAuthentication no` dans `sshd_config`, la connexion par mot de passe était encore acceptée.  
**Diagnostic** : Un fichier `/etc/ssh/sshd_config.d/50-cloud-init.conf` propre aux images cloud OVH contenait `PasswordAuthentication yes` et écrasait la config principale.  
**Solution** : Modification du fichier cloud-init puis redémarrage SSH.

```bash
sudo nano /etc/ssh/sshd_config.d/50-cloud-init.conf
# Remplacer PasswordAuthentication yes par PasswordAuthentication no
sudo systemctl restart ssh
```

---

### 6. `settings.py` incorrect persistant malgré les redéploiements

**Problème** : Django affichait une erreur `DisallowedHost` avec `predi_lection-app.duckdns.org` (underscore) malgré plusieurs releases censées corriger le domaine en `predi-lection-app.duckdns.org` (tiret).  
**Diagnostic** : Le volume Docker `django_data` monté sur `/app/` persistait entre les redéploiements. L'ancien `settings.py` avec l'underscore était conservé dans le volume et écrasait celui de la nouvelle image au démarrage. `docker compose up -d` ne recrée pas les volumes existants.  
**Solution** : Suppression complète des volumes et des images pour repartir d'un état propre.

```bash
docker compose -f docker-compose.yaml down -v
docker system prune -af
docker compose -f docker-compose.yaml pull
docker compose -f docker-compose.yaml up -d
```
---

## Améliorations envisagées

- Ajouter une sauvegarde automatique de la base de données PostgreSQL
- Mettre en place un monitoring (Prometheus + Grafana)
- Utiliser un vrai nom de domaine payant en production (DuckDNS n'est pas garanti)
- Haute disponibilité : plusieurs VPS avec load balancer