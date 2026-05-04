# Guide de déploiement — EVER Suivi Affectation

> Pour : équipe ops (Vincent).
> Mis à jour : mai 2026.

---

## Architecture cible

```
Internet
   │
   ▼
[Nginx Proxy Manager]  (réseau Docker : nginx-proxy-manager_default)
   │  ever.ifop.com → :8000
   ▼
[Container ever-suivi]  (gunicorn 3 workers)
   │
   ▼
[SQL Server SRV-LANSQL-03\MSSQLIFOPGE]  (base EVER, compte ever_app)
```

Les fichiers statiques sont servis directement par **Whitenoise** (pas de volume nginx dédié).
Les logs et sessions Django sont montés en volumes Docker nommés.

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
- Réseau `nginx-proxy-manager_default` existant
- SSH configuré (clé publique du poste dev autorisée)

---

## Variables d'environnement

Créer un fichier `.env` sur le serveur (ne jamais committer ce fichier) :

```dotenv
# Django
SECRET_KEY=<clé aléatoire 50+ caractères>
DEBUG=False
ALLOWED_HOSTS=ever.ifop.com

# SQL Server
DB_HOST=SRV-LANSQL-03\MSSQLIFOPGE
DB_NAME=EVER
DB_USER=ever_app
DB_PASSWORD=<mot de passe ever_app>

# Mots de passe applicatifs
FIRST_LOGIN_PASSWORD=<mdp premier login>
ADMIN_PASSWORD=<mdp confirmation affectation>
```

> ⚠️ Si le mot de passe `DB_PASSWORD` contient `;`, il doit être entouré d'accolades
> dans la chaîne de connexion ODBC : `{mot;de;passe}`. Ce traitement est automatique
> dans `accounts/db.py`.

---

## Procédure de déploiement

### 1. Construire l'image (depuis le poste dev)

```bash
cd C:\Users\y_bicrel\source\repos\suivi-affectation-ever

# Build
docker build -t localhost:5000/ever-suivi:latest .

# Push vers le registry interne
docker push localhost:5000/ever-suivi:latest
```

### 2. Déployer sur le serveur

```bash
# Se connecter au serveur
ssh <user>@srv-dbapps-01

# Aller dans le dossier du projet (ou le créer)
mkdir -p ~/ever && cd ~/ever

# Copier docker-compose.yml et .env si pas déjà présents
# scp docker-compose.yml .env <user>@srv-dbapps-01:~/ever/

# Récupérer la nouvelle image et redémarrer
docker compose pull
docker compose up -d
```

### 3. Vérifier le démarrage

```bash
# Logs en temps réel
docker compose logs -f

# Vérifier que le container est bien UP
docker compose ps

# Test HTTP rapide
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login/
# → doit retourner 200
```

---

## Mise à jour (déploiement continu)

```bash
# Depuis le poste dev
docker build -t localhost:5000/ever-suivi:latest .
docker push localhost:5000/ever-suivi:latest

# Sur le serveur
ssh <user>@srv-dbapps-01 "cd ~/ever && docker compose pull && docker compose up -d"
```

---

## Volumes Docker

| Volume | Contenu | Localisation dans le container |
|--------|---------|-------------------------------|
| `ever_logs` | Logs gunicorn (accès + erreurs) | `/app/logs/` |
| `ever_sessions` | Fichiers de session Django | `/app/sessions/` |

```bash
# Lire les logs gunicorn
docker compose exec web tail -100 /app/logs/gunicorn-error.log

# Lire les logs applicatifs Django
docker compose exec web tail -100 /app/logs/ever.log
```

---

## Réseau — Nginx Proxy Manager

Le container s'attache au réseau externe `nginx-proxy-manager_default`.
Dans l'interface NPM, créer un **Proxy Host** :

| Champ | Valeur |
|-------|--------|
| Domain | `ever.ifop.com` |
| Scheme | `http` |
| Forward Hostname | `ever-suivi` *(nom du service docker-compose)* |
| Forward Port | `8000` |
| SSL | Let's Encrypt (si accessible depuis internet) ou certificat interne |

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

# Créer le fichier .env local (pointer sur EVER_DEV)
# DB_HOST=SRV-LANSQL-03\MSSQLIFOPGE
# DB_NAME=EVER_DEV
# ...

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
| Container redémarre en boucle | Erreur au collectstatic ou ODBC manquant | `docker compose logs web` |
| Sessions perdues après redémarrage | Volume `ever_sessions` non monté | Vérifier le `docker-compose.yml` |
| Page blanche sans erreur | `DEBUG=False` + `ALLOWED_HOSTS` incorrect | Ajouter le domaine dans `ALLOWED_HOSTS` |
