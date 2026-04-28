1. Installer uv

``` curl -Ls https://astral.sh/uv/install.sh | bash ```

2. Recharger le terminal (zsh) 

``` source ~/.zshrc```

3. Vérifier l’installation

``` uv --version ```

Si la commande ne fonctionne pas


export PATH="$HOME/.local/bin:$PATH"
source ~/.zshrc 



1. Supprimer l’ancien environnement

```  rm -rf .venv ```

2. Recréer avec uv

``` uv venv ```
``` source .venv/bin/activate ```

3. Installer les dépendances

``` uv sync ```

Ajouter une dépendance

``` uv add nom_du_package ```

