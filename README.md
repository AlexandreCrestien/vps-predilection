# Predilection — README

## Contexte et projet

Application Data/IA de prédiction des résultats électoraux par commune, développée lors d'un projet précédent. Elle est composée de 3 services : une API FastAPI, une application web Django et une base de données PostgreSQL. Un service d'ingestion charge les données CSV au démarrage.

L'objectif de ce projet est de déployer cette application sur un VPS OVH de manière sécurisée, reproductible et traçable.

---

## Prérequis

- Un VPS OVH sous Ubuntu
- Un compte GitHub avec accès au dépôt
- Docker et Docker Compose installés sur le VPS
- Un nom de domaine (DuckDNS suffit)
- Un token GitHub avec le scope `read:packages` pour puller les images

---

## Architecture retenue

```
GitHub (code + registry ghcr.io)
        │
        │  push develop → CI/CD (lint, tests, build, push images)
        │  release vX.X → CI/CD + déploiement automatique sur VPS
        ▼
VPS OVH (Ubuntu)
        │
        ├── Traefik (reverse proxy, HTTPS Let's Encrypt)
        │       ├── predilection.duckdns.org       → Django (8000)
        │       ├── api.predilection.duckdns.org   → FastAPI (8080)
        │       └── dashboard.predilection.duckdns.org → Dashboard Traefik
        │
        ├── Django     (interface web)
        ├── FastAPI    (API + modèle ML)
        ├── PostgreSQL (base de données, non exposé publiquement)
        └── Ingest     (one-shot, charge le CSV au démarrage)
```

---

## Services et ports

| Service    | Port interne | URL publique                                       |
|------------|-------------|----------------------------------------------------|
| Django     | 8000        | https://predilection.duckdns.org                   |
| FastAPI    | 8080        | https://api.predilection.duckdns.org               |
| Traefik    | 80 / 443    | https://dashboard.predilection.duckdns.org         |
| PostgreSQL | 5432        | non exposé publiquement                            |

---

## Procédure d'installation sur un VPS neuf

Voir le fichier [`docs/DEPLOY.md`](docs/DEPLOY.md) pour la procédure complète étape par étape (sécurisation SSH, pare-feu, Docker, Traefik, CI/CD).

---

## Procédure de déploiement initial

Le déploiement initial se fait **une seule fois manuellement** avant que la CI/CD prenne le relais.

**Depuis la machine locale**, copier le `docker-compose.yaml` sur le VPS :

```bash
scp -i ~/.ssh/ovh_predilection -P 49200 docker-compose.yaml ubuntu@<IP>:~/political-prediction/
```

**Sur le VPS**, préparer l'environnement :

```bash
mkdir -p ~/political-prediction/letsencrypt
cd ~/political-prediction

# Créer le fichier .env (voir la liste des variables dans docs/DEPLOY.md)
nano .env

# Se connecter à ghcr.io
echo "TON_GITHUB_TOKEN" | docker login ghcr.io -u TON_USERNAME --password-stdin

# Lancer les services
docker compose pull
docker compose up -d

# Vérifier
docker compose ps
```

Configurer ensuite les secrets GitHub Actions (voir [`docs/DEPLOY.md`](docs/DEPLOY.md)) pour activer le déploiement automatique.

---

## Procédure de publication d'une nouvelle release

1. Faire les modifications sur la branche `develop`
2. Pusher sur `develop` → le workflow build et publie les images taguées `develop`
3. Créer une release GitHub (`vX.X`) → déploiement automatique sur le VPS avec le nouveau tag

```
GitHub → Releases → Create a new release → Tag: vX.X → Publish release
```

---

## Consulter les logs

**Logs des services Docker**

```bash
# Logs d'un service spécifique
docker compose logs django
docker compose logs fastapi
docker compose logs traefik
docker compose logs postgres

# Logs en temps réel
docker compose logs -f django
docker compose logs -f fastapi

# Dernières N lignes
docker compose logs --tail=100 django

# Filtrer par niveau
docker compose logs fastapi | grep -i "error"
docker compose logs django | grep -i "warning"
docker compose logs traefik | grep -i "error"

# Ingest (one-shot, vérifier qu'il a bien tourné)
docker compose logs ingest
```

**Logs via Docker directement**

```bash
docker logs traefik
docker logs traefik -f --tail=50
```

**Logs système**

```bash
# Tentatives de connexion SSH
sudo journalctl -u ssh

# Activité Fail2ban (bans, tentatives bloquées)
sudo journalctl -u fail2ban
```

**Statut et ressources**

```bash
# Statut des conteneurs
docker compose ps

# Consommation CPU / RAM en temps réel
docker stats

# Inspecter un conteneur
docker inspect traefik
```

---

## Mesures de sécurité

- Connexion SSH par clé uniquement (désactivation du mot de passe via `sshd_config` et `50-cloud-init.conf`)
- Port SSH non standard (49200)
- Pare-feu iptables : seuls les ports 80, 443 et 49200 sont ouverts
- Fail2ban : blocage après 3 tentatives SSH échouées en 5 minutes
- Utilisateur de déploiement dédié avec droits Docker uniquement
- Services applicatifs non exposés directement (FastAPI, Django, PostgreSQL accessibles uniquement via Traefik ou le réseau Docker interne)
- Dashboard Traefik protégé par authentification Basic Auth
- Secrets gérés via GitHub Actions Secrets (jamais dans le dépôt)
- HTTPS avec certificat Let's Encrypt via Traefik
- `.env` listé dans `.gitignore`

---

## Limites de la solution

- VPS pédagogique : pas de haute disponibilité, pas de sauvegarde automatique de la base de données
- Un seul VPS : pas de redondance en cas de panne matérielle
- DuckDNS est un service gratuit non garanti en production
- Les images Docker sont publiques sur ghcr.io