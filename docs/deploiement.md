# Guide de déploiement — EVER Suivi Affectation

> Pour : équipe ops (Vincent) et dev (Yann).
> Mis à jour : mai 2026.

---

## Architecture cible

```
Internet
   │
   ▼
[Nginx Proxy Manager]  (réseau Docker : nginx-proxy-manager_default)
   │  ever.ifop.com → ever-suivi:8000
   ▼
[Container ever-suivi]  (gunicorn 3 workers)
   │
   ▼
[SQL Server SRV-LANSQL-03\MSSQLIFOPGE]  (base EVER, compte ever_app)
```

Les fichiers statiques sont servis directement par **Whitenoise** (pas de volume nginx dédié).
Les logs gunicorn vont sur stdout/stderr → visibles dans Portainer.
Les sessions Django sont montées en volume Docker nommé.

---

## Prérequis

### Côté SQL Server
- Base `EVER` (ou `EVER_DEV` pour les tests)
- Compte SQL `ever_app` avec les droits `EXECUTE` sur toutes les TVFs et procédures EVER
- Script de référence : `sql/grant_ever_app.sql`

```sql
-- Vérification rapide des droits
SELECT OBJECT_NAME(major_id), permission_name
FROM sys.database_permissions
WHERE grantee_principal_id = USER_ID('ever_app')
ORDER BY 1;
```

### Côté serveur Docker (`srv-dbapps-01`)
- Docker Engine installé
- Registry interne accessible : `localhost:5000`
- Réseau `nginx-proxy-manager_default` existant (créé par la stack NPM)
- Accès à Portainer : `https://portainer.ifop.com`

---

## Variables d'environnement

Les variables sont saisies directement dans Portainer (section "Environment variables" de la stack).
**Ne jamais committer de valeurs réelles dans le dépôt git.**

| Variable | Exemple / Description |
|----------|----------------------|
| `SECRET_KEY` | Chaîne aléatoire 50+ caractères — **sans `$`** (docker-compose interpréterait `$x` comme variable) |
| `ALLOWED_HOSTS` | `ever.ifop.com,srv-dbapps-01` |
| `DB_HOST` | `SRV-LANSQL-03\MSSQLIFOPGE` |
| `DB_NAME` | `EVER` (prod) ou `EVER_DEV` (test) |
| `DB_USER` | `ever_app` |
| `DB_PASSWORD` | Mot de passe ever_app (caractères spéciaux OK, gérés automatiquement) |
| `FIRST_LOGIN_PASSWORD` | Mot de passe générique première connexion |
| `ADMIN_PASSWORD` | Mot de passe confirmation affectation |

> ⚠️ **SECRET_KEY** : ne pas utiliser de caractères `$` — docker-compose les interprète comme
> des variables d'environnement. Générer avec :
> `python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#%^&*(-_=+)') for _ in range(50)))"`

> ⚠️ **DB_PASSWORD** : si le mot de passe contient `;` ou `}`, c'est géré automatiquement
> dans `accounts/db.py` (wrapping ODBC `{...}`).

---

## Procédure de déploiement (via Portainer)

Le déploiement se fait entièrement depuis **Portainer** — pas besoin d'accès SSH.

### 1. Préparer le tarball de build

Depuis le poste dev, générer l'archive de build (Dockerfile à la racine) :

```python
# Exécuter depuis la racine du projet
import tarfile, pathlib

root = pathlib.Path('.')
out  = pathlib.Path('ever-suivi-build.tar.gz')
SKIP = {'.git', '.venv', '__pycache__', 'staticfiles', '.env'}

with tarfile.open(out, 'w:gz') as tf:
    for p in root.rglob('*'):
        if any(part in SKIP or part.startswith('__pycache__') for part in p.parts):
            continue
        if p.suffix == '.pyc':
            continue
        tf.add(p, arcname=str(p))
```

Ou via le script Python fourni (à la racine du projet) :
```bash
python make_tarball.py
# → génère ever-suivi-build.tar.gz
```

### 2. Construire l'image dans Portainer

1. **Portainer → Images → Build a new image**
2. **Name** : `localhost:5000/ever-suivi:latest`
3. **Build method** : `Upload` → sélectionner `ever-suivi-build.tar.gz`
4. Cliquer **Build the image**
5. Attendre la fin du build (logs visibles dans l'onglet Output)
6. Vérifier que l'image apparaît dans **Images** avec le tag `localhost:5000/ever-suivi:latest`

### 3. Créer ou mettre à jour la stack

#### Premier déploiement

1. **Portainer → Stacks → Add stack**
2. **Name** : `ever-suivi`
3. **Build method** : `Web editor` → coller le contenu de `docker-compose.yml`
4. **Environment variables** : renseigner toutes les variables du tableau ci-dessus
5. Cliquer **Deploy the stack**

#### Mise à jour (nouvelle version)

1. Rebuilder l'image (étape 1-2 ci-dessus)
2. **Portainer → Stacks → ever-suivi → Editor**
3. Cliquer **Update the stack** — **sans cocher** "Re-pull image"
   *(l'image est locale, pas dans un registry externe)*

---

## Nginx Proxy Manager

Le container `ever-suivi` est sur le réseau `nginx-proxy-manager_default` avec le hostname
`ever-suivi`. NPM peut donc lui router le trafic directement par nom de container.

Dans l'interface NPM, créer un **Proxy Host** :

| Champ | Valeur |
|-------|--------|
| Domain Names | `ever.ifop.com` |
| Scheme | `http` |
| Forward Hostname / IP | `ever-suivi` |
| Forward Port | `8000` |
| Cache Assets | off |
| Block Common Exploits | on |
| SSL | certificat interne IFOP ou Let's Encrypt |

---

## Volumes Docker

| Volume | Contenu | Note |
|--------|---------|------|
| `ever_sessions` | Fichiers de session Django | Persisté entre redémarrages |
| `ever_logs` | Répertoire logs (non utilisé en prod) | Logs sur stdout en prod |

---

## Vérification post-déploiement

Dans **Portainer → Containers → ever-suivi → Logs**, les lignes attendues au démarrage :

```
[INFO] Starting gunicorn 26.0.0
[INFO] Listening at: http://0.0.0.0:8000
[INFO] Using worker: sync
[INFO] Booting worker with pid: X   (× 3)
```

L'absence d'erreur `[ERROR]` ou `[CRITICAL]` confirme que Django démarre correctement.

---

## Environnement de développement local

```bash
# Cloner le repo
git clone <url-repo> suivi-affectation-ever
cd suivi-affectation-ever

# Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier .env local
cp .env.example .env
# → éditer .env : pointer sur EVER_DEV, renseigner les mots de passe

# Lancer le serveur de développement
python manage.py runserver
# → http://127.0.0.1:8000
```

> Le driver **ODBC 17 pour SQL Server** doit être installé sur le poste :
> https://learn.microsoft.com/fr-fr/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## Dépannage

| Symptôme | Cause probable | Action |
|----------|---------------|--------|
| `500` sur toutes les pages | Connexion DB échouée | Vérifier `DB_HOST`, `DB_PASSWORD`, droits `ever_app` |
| "Identifiant inconnu" au login | TVF `ft_EVER_Utilisateur` absente ou droits manquants | Relancer `grant_ever_app.sql` |
| Container redémarre en boucle | Erreur Django au démarrage | Portainer → Logs du container |
| Sessions perdues après redémarrage | Volume `ever_sessions` non monté | Vérifier le `docker-compose.yml` |
| Page blanche sans erreur | `DEBUG=False` + `ALLOWED_HOSTS` incorrect | Ajouter le domaine dans `ALLOWED_HOSTS` |
| Build image échoue "NO_PUBKEY" | Clé GPG Microsoft non reconnue | Vérifier le Dockerfile (méthode `gpg --dearmor`) |
| "manifest unknown" au redeploy | Image locale, pas dans registry | Décocher "Re-pull image" dans Portainer |
| Variables `$x` vides au démarrage | `SECRET_KEY` contient des `$` | Régénérer la clé sans caractères `$` |
