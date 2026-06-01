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
        │       ├── predilection.duckdns.org → Django (8000)
        │       ├── api.predilection.duckdns.org → FastAPI (8080)
        │       └── dashboard.predilection.duckdns.org → Dashboard Traefik
        │
        ├── Django (interface web)
        ├── FastAPI (API + modèle ML)
        ├── PostgreSQL (base de données)
        └── Ingest (one-shot, charge le CSV au démarrage)
```

---

## Services et ports

| Service    | Port interne | URL publique                          |
|------------|-------------|---------------------------------------|
| Django     | 8000        | https://predilection.duckdns.org      |
| FastAPI    | 8080        | https://api.predilection.duckdns.org  |
| Traefik    | 80 / 443    | https://dashboard.predilection.duckdns.org |
| PostgreSQL | 5432        | non exposé publiquement               |

---

## Procédure d'installation sur un VPS neuf

Voir le fichier `DEPLOY.md` pour la procédure complète étape par étape (sécurisation, Docker, Traefik, CI/CD).

---

## Procédure de déploiement initial

1. Cloner le dépôt sur la machine locale
2. Configurer les secrets GitHub (voir `DEPLOY.md`)
3. Créer une release `v1.0` sur GitHub
4. Le workflow CI/CD build les images, les publie sur ghcr.io et déploie sur le VPS automatiquement

---

## Procédure de publication d'une nouvelle release

1. Faire les modifications dans le code sur la branche `develop`
2. Pusher sur `develop` → le workflow build et publie les images taguées `develop`
3. Créer une release GitHub (`vX.X`) → déploiement automatique sur le VPS avec le nouveau tag

---

## Consulter les logs

```bash
# Logs d'un service
docker compose logs django
docker compose logs fastapi
docker compose logs traefik

# Logs en temps réel
docker compose logs -f django

# Statut des conteneurs
docker compose ps
```

---

## Mesures de sécurité

- Connexion SSH par clé uniquement (pas de mot de passe)
- Port SSH non standard (49200)
- Pare-feu iptables : seuls les ports 80, 443 et 49200 sont ouverts
- Fail2ban : blocage après 3 tentatives SSH échouées en 5 minutes
- Utilisateur de déploiement dédié (`panda`) avec droits Docker uniquement
- Dashboard Traefik protégé par authentification Basic Auth
- Secrets gérés via GitHub Actions Secrets (jamais dans le dépôt)
- HTTPS avec certificat Let's Encrypt via Traefik

---

## Limites de la solution

- VPS pédagogique : pas de haute disponibilité, pas de sauvegarde automatique
- Un seul VPS : pas de redondance en cas de panne
- Le modèle ML présente des erreurs sur certaines communes (données historiques incomplètes)
- DuckDNS est un service gratuit non garanti en production
- Les images Docker sont publiques sur ghcr.io