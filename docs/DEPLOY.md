# Documentation de déploiement

## J1 — VPS et sécurisation minimale

**Connexion au VPS via un mot de passe**
```bash
ssh ubuntu@<IP>
```

**Création d'un utilisateur de déploiement**
```bash
sudo adduser deploy
```

**Création d'une clé SSH**
- https://docs.ovhcloud.com/fr/guides/bare-metal-cloud/dedicated-servers/creating-ssh-keys
```bash
ssh-keygen -t ed25519 -a 100
# Entrer le chemin complet de la nouvelle clé (ex : /home/simplon/.ssh/ovh_predilection)
```

**Association de la clé SSH au serveur VPS**
```bash
cat ~/.ssh/ovh_predilection.pub  # copier le contenu
```

Pour l'utilisateur Ubuntu :
```bash
nano ~/.ssh/authorized_keys  # coller la clé, quitter avec Ctrl+X
```

Pour l'utilisateur deploy (depuis ubuntu) :
```bash
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Nouvelles commandes de connexion :
```bash
ssh -i ~/.ssh/ovh_predilection ubuntu@<IP>
ssh -i ~/.ssh/ovh_predilection deploy@<IP>
```

---

**Configurer le SSH**
- https://docs.ovhcloud.com/fr/guides/bare-metal-cloud/virtual-private-servers/secure-your-vps
```bash
sudo nano /lib/systemd/system/ssh.socket
# Dans les 2 lignes ListenStream, remplacer 22 par 49200 (entre 49152 et 65535)
sudo systemctl daemon-reload
sudo systemctl restart ssh.socket
```

Nouvelles commandes de connexion :
```bash
ssh ubuntu@<IP> -p 49200
ssh deploy@<IP> -p 49200
```

---

**Désactiver l'authentification par mot de passe SSH**

> **Prérequis** : avoir une clé SSH fonctionnelle configurée sur le VPS avant de commencer.

Sur Ubuntu (notamment les images cloud OVH), un fichier peut **écraser** la config principale. Vérifier tous les fichiers concernés :

```bash
sudo grep -r "PasswordAuthentication" /etc/ssh/
```

Modifier **tous** les fichiers qui contiennent `PasswordAuthentication yes` :

```bash
sudo nano /etc/ssh/sshd_config
sudo nano /etc/ssh/sshd_config.d/50-cloud-init.conf  # présent sur les VPS OVH
```

Mettre à `no` dans chaque fichier :

```
PasswordAuthentication no
PermitEmptyPasswords no
```

Redémarrer SSH :

```bash
sudo systemctl restart ssh
```

Vérifier depuis un autre PC dans un **nouveau terminal** (garder la session actuelle ouverte) :

```bash
# Doit échouer
ssh -o PreferredAuthentications=password ubuntu@<IP> -p 49200
# Résultat attendu : Permission denied (publickey).

# Doit fonctionner
ssh -i ~/.ssh/ovh_predilection ubuntu@<IP> -p 49200
```

---

**Configurer le pare-feu**
- https://docs.ovhcloud.com/fr/guides/bare-metal-cloud/virtual-private-servers/firewall-linux-iptable
```bash
sudo apt-get install iptables
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 49200 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 1 -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -j DROP
sudo iptables -L  # vérification
sudo iptables-save > /etc/iptables/rules.v4
```

---

**Configurer Fail2Ban**
- https://docs.ovhcloud.com/fr/guides/bare-metal-cloud/virtual-private-servers/secure-your-vps
```bash
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Remplacer dans la section `[sshd]` :
```ini
enabled = true
port = 49200
filter = sshd
maxretry = 3
findtime = 5m
bantime  = 30m
logpath = %(sshd_log)s
backend = %(sshd_backend)s
```

```bash
sudo systemctl restart fail2ban
sudo systemctl status fail2ban  # vérification
```

---

**Installation de Docker**
- https://docs.docker.com/engine/install/ubuntu/

```bash
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Ajouter le dépôt à Apt sources :
```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world  # vérification
sudo usermod -aG docker deploy
```

---

## J2 — Déploiement Docker et reverse proxy

**Installer et configurer Traefik**
- https://doc.traefik.io/traefik/setup/docker/

```bash
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/local.key -out certs/local.crt \
  -subj "/CN=*.docker.localhost"
sudo apt install apache2-utils
htpasswd -nb admin "P@ssw0rd" | sed -e 's/\$/\$\$/g'
# Copier la clé générée
```

Créer un dossier `dynamic` avec un fichier `tls.yaml` :
```yaml
tls:
  certificates:
    - certFile: /certs/local.crt
      keyFile:  /certs/local.key
```

**Contenu du `docker-compose.yaml`** (remplacer `PASTE_HASH` par la clé générée) :
```yaml
services:
  traefik:
    image: traefik:v3.7
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./certs:/certs:ro
      - ./dynamic:/dynamic:ro
    command:
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.web.http.redirections.entrypoint.permanent=true"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.websecure.http.tls=true"
      - "--providers.file.filename=/dynamic/tls.yaml"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=proxy"
      - "--api.dashboard=true"
      - "--api.insecure=false"
      - "--log.level=INFO"
      - "--accesslog=true"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`dashboard.docker.localhost`)"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.tls=true"
      - "traefik.http.middlewares.dashboard-auth.basicauth.users=PASTE_HASH"
      - "traefik.http.routers.dashboard.middlewares=dashboard-auth@docker"

  postgres:
    image: postgres:15
    restart: always
    networks:
      - proxy
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  ingest:
    build:
      context: .
      dockerfile: scripts/Dockerfile
    networks:
      - proxy
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
    restart: "no"

  fastapi:
    build:
      context: ./api
      dockerfile: Dockerfile
    networks:
      - proxy
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.fastapi.rule=Host(`api.docker.localhost`)"
      - "traefik.http.routers.fastapi.entrypoints=websecure"
      - "traefik.http.routers.fastapi.tls=true"
      - "traefik.http.services.fastapi.loadbalancer.server.port=8080"

  django:
    build:
      context: ./django_political_app
      dockerfile: Dockerfile
    networks:
      - proxy
    depends_on:
      - fastapi
    environment:
      DEBUG: ${DEBUG}
      SECRET_KEY: ${SECRET_KEY}
      BASE_URL_LOCAL: http://fastapi:8080
      BASE_URL: https://geo.api.gouv.fr
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.django.rule=Host(`app.docker.localhost`)"
      - "traefik.http.routers.django.entrypoints=websecure"
      - "traefik.http.routers.django.tls=true"
      - "traefik.http.services.django.loadbalancer.server.port=8000"

networks:
  proxy:
    name: proxy

volumes:
  postgres_data:
```

Dans `settings.py` de Django :
```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'app.docker.localhost']
CSRF_TRUSTED_ORIGINS = ['https://app.docker.localhost']
```

```bash
docker compose up -d
# Dashboard : https://dashboard.docker.localhost/dashboard/ (admin / P@ssw0rd)
# Site : https://app.docker.localhost/
```

---

**Configurer DuckDNS**
- Aller sur https://www.duckdns.org/ et se connecter avec GitHub
- Choisir un nom de domaine (ex : `predilection`) puis faire `add domain`
- Remplacer le `current ip` par l'IP du VPS

Dans `settings.py` :
```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'predilection.duckdns.org']
CSRF_TRUSTED_ORIGINS = ['https://predilection.duckdns.org']
```

Remplacer dans le `docker-compose.yaml` pour fastapi et django :
```yaml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.fastapi.rule=Host(`api.predilection.duckdns.org`)"
      - "traefik.http.routers.fastapi.entrypoints=websecure"
      - "traefik.http.routers.fastapi.tls=true"
      - "traefik.http.routers.fastapi.tls.certresolver=myresolver"
      - "traefik.http.services.fastapi.loadbalancer.server.port=8080"
```

Remplacer dans le service Traefik du `docker-compose.yaml` (modifier `EMAIL` + `PASTE_HASH`) :
- https://doc.traefik.io/traefik/https/acme/
```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    command:
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.web.http.redirections.entrypoint.permanent=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=proxy"
      - "--certificatesresolvers.myresolver.acme.email=EMAIL"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.myresolver.acme.httpchallenge=true"
      - "--certificatesresolvers.myresolver.acme.httpchallenge.entrypoint=web"
      - "--api.dashboard=true"
      - "--api.insecure=false"
      - "--log.level=INFO"
      - "--accesslog=true"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`dashboard.predilection.duckdns.org`)"
      - "traefik.http.routers.dashboard.entrypoints=websecure"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.tls=true"
      - "traefik.http.routers.dashboard.tls.certresolver=myresolver"
      - "traefik.http.middlewares.dashboard-auth.basicauth.users=PASTE_HASH"
      - "traefik.http.routers.dashboard.middlewares=dashboard-auth@docker"
```

---

## J3 — Registry, CI/CD et release

**Modification du `docker.yml` pour le CI/CD**
- https://docs.github.com/fr/actions/tutorials/publish-packages/publish-docker-images

Remplacer les étapes de build par les actions officielles Docker :
```yaml
env:
  REGISTRY: ghcr.io

      - name: Log in to the Container registry
        uses: docker/login-action@65b78e6e13532edd9afa3aa52ac7964289d1a9c1
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata for FastAPI
        id: meta-fastapi
        uses: docker/metadata-action@9ec57ed1fcdbf14dcef7dfbe97b2010124a938b7
        with:
          images: ${{ env.REGISTRY }}/TON_USERNAME/fastapi-app

      - name: Build and push FastAPI
        uses: docker/build-push-action@f2a1d5e99d037542a71f64918e516c093c6f3fc4
        with:
          context: ./api
          push: true
          tags: ${{ steps.meta-fastapi.outputs.tags }}
          labels: ${{ steps.meta-fastapi.outputs.labels }}

      # Répéter pour Django (context: ./django_political_app)
      # et Ingest (context: . / file: ./scripts/Dockerfile)
```

---

**Ajout des secrets GitHub Actions**
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=predilection
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/predilection
DEBUG=True
SECRET_KEY=ta_secret_key
ACME_EMAIL=ton_email
DASHBOARD_AUTH=hash_genere_par_htpasswd
DOMAIN=predilection.duckdns.org
VPS_HOST=IP du VPS
VPS_USER=deploy
VPS_PORT=49200
VPS_SSH_KEY=clé privée SSH (voir ci-dessous)
```

**Générer la clé SSH pour GitHub Actions (sur le VPS)** :
```bash
ssh-keygen -t ed25519 -C "github-actions-vps" -f ~/.ssh/github_actions_vps
cat ~/.ssh/github_actions_vps.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/github_actions_vps  # copier dans le secret VPS_SSH_KEY
```

**Modifier le trigger du workflow** :
```yaml
on:
  push:
    branches: [ "develop" ]
  release:
    types: [published]
```

**Ajouter les étapes de déploiement dans le workflow** :
```yaml
      - name: Copy docker-compose to VPS
        if: github.event_name == 'release'
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          port: ${{ secrets.VPS_PORT }}
          source: "docker-compose.yaml"
          target: "~/political-prediction/"

      - name: Deploy on VPS
        if: github.event_name == 'release'
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          port: ${{ secrets.VPS_PORT }}
          script: |
            mkdir -p ~/political-prediction/letsencrypt
            cd ~/political-prediction
            cat > .env << 'EOF'
            POSTGRES_USER=${{ secrets.POSTGRES_USER }}
            POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
            POSTGRES_DB=${{ secrets.POSTGRES_DB }}
            DATABASE_URL=${{ secrets.DATABASE_URL }}
            DEBUG=${{ secrets.DEBUG }}
            SECRET_KEY=${{ secrets.SECRET_KEY }}
            ACME_EMAIL=${{ secrets.ACME_EMAIL }}
            DASHBOARD_AUTH=${{ secrets.DASHBOARD_AUTH }}
            DOMAIN=${{ secrets.DOMAIN }}
            EOF
            echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            sed -i "s|:develop|:${{ github.ref_name }}|g" docker-compose.yaml
            docker image prune -f
            docker compose -f docker-compose.yaml pull
            docker compose -f docker-compose.yaml up -d
```

**Publier une release** :
- GitHub → Releases → Create a new release
- Tag : `v1.x` / Title : description du changement
- Publish release → déploiement automatique sur le VPS