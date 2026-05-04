# EVER 2026 — Suivi & Affectation

Application web interne IFOP / Sociovision pour le suivi en temps réel des vacations
d'enquête et l'affectation des enquêteurs sur l'étude EVER 2026.

---

## Fonctionnalités

| Page | Description |
|------|-------------|
| **Suivi Aéroport** | Tableau de bord hiérarchique (aéroport → vol → vacation) avec taux de réalisation, recrutés, valides, abandons. Export CSV. |
| **Suivi Hors Aéroport** | Tableau de bord par zone d'enquête (autoroutes, gares…) avec mêmes indicateurs. |
| **Affectation** | Affectation/désaffectation d'enquêteurs aux vacations (protégée par mot de passe). |
| **Commentaires** | Ajout de commentaires avant/après vacation depuis les deux pages de suivi. |

---

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Backend | Python 3.12 · Django 4.2 |
| Base de données | SQL Server (EVER / EVER_DEV) via pyodbc + ODBC 17 |
| Frontend | Bootstrap 5 · Bootstrap Icons · jQuery · Flatpickr |
| Fichiers statiques | Whitenoise (intégré Django) |
| Serveur de prod | Gunicorn 3 workers derrière Nginx Proxy Manager |
| Déploiement | Docker · registry interne `localhost:5000` |

---

## Structure du projet

```
suivi-affectation-ever/
├── accounts/               # Authentification (login, logout, session, rôles)
│   ├── db.py               # Connexion SQL Server + login via ft_EVER_Utilisateur
│   ├── roles.py            # Définition des rôles et droits (DROITS dict)
│   └── views.py            # Vues login/logout/set-password
│
├── core/                   # Module principal (suivi + affectation)
│   ├── db.py               # Couche données : appels TVFs + normalisation colonnes
│   ├── views.py            # Vues HTML + endpoints API AJAX
│   ├── urls.py             # Routes
│   └── templates/core/
│       ├── base.html       # Master page (header, nav, modales)
│       ├── suivi_aeroport.html
│       ├── suivi_hors_aeroport.html
│       └── affectation.html
│
├── static/
│   ├── css/ever.css        # Styles IFOP (palette bleu #10218b)
│   └── js/
│       ├── ever.js         # JS partagé (horloge, spinner, commentaires, fmtDate)
│       ├── suivi_aeroport.js
│       ├── suivi_hors_aeroport.js
│       └── affectation.js
│
├── ever_project/           # Configuration Django
│   └── settings.py
│
├── docs/
│   ├── tvf_mapping.md      # Cartographie TVFs → API → JSON (référence Philippe)
│   └── deploiement.md      # Guide déploiement Docker (référence Vincent)
│
├── sql/
│   └── grant_ever_app.sql  # Droits SQL à passer sur la base EVER
│
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Démarrage rapide (développement local)

### Prérequis

- Python 3.11 ou 3.12
- [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/fr-fr/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Accès réseau à `SRV-LANSQL-03\MSSQLIFOPGE` (base `EVER_DEV`)

### Installation

```bash
git clone <url-repo> suivi-affectation-ever
cd suivi-affectation-ever

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Créer un fichier `.env` à la racine (non commité) :

```dotenv
SECRET_KEY=dev-secret-key-not-for-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_HOST=SRV-LANSQL-03\MSSQLIFOPGE
DB_NAME=EVER_DEV
DB_USER=ever_app
DB_PASSWORD=<mot de passe ever_app>

FIRST_LOGIN_PASSWORD=<mdp premier login>
ADMIN_PASSWORD=<mdp confirmation affectation>
```

### Lancement

```bash
python manage.py runserver
# → http://127.0.0.1:8000
```

Se connecter avec un login de la table `dbo.Utilisateur` (ex : `BICREL_Y`).

---

## Rôles et accès

| Rôle | Suivi aéro | Suivi hors aéro | Affectation | Commentaires | Filtre enquêteur |
|------|:----------:|:---------------:|:-----------:|:------------:|:----------------:|
| `ADMIN_IFOP` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `RESPONSABLE_IFOP` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `RESPONSABLE_ST` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `SUPERVISEUR_IFOP` | ✅ | ✅ | — | ✅ | ✅ |
| `SUPERVISEUR_ST` | ✅ | ✅ | — | ✅ | ✅ |
| `ENQUETEUR` | ✅ | ✅ | — | — | — |
| `CLIENT` | ✅ | ✅ | — | — | — |

L'affectation nécessite en plus la saisie d'un mot de passe (`ADMIN_PASSWORD`) à la première
modification de la session.

---

## Intervenants

| Rôle | Personne | Périmètre |
|------|----------|-----------|
| Dev / intégration | Yann Bicrel (IFOP / Sociovision) | Application Django, JS, CSS |
| DBA / TVFs | Philippe | SQL Server, TVFs, procédures stockées |
| Ops / déploiement | Vincent | Serveur `srv-dbapps-01`, Docker, SSH, NPM |

---

## Déploiement production

Voir [`docs/deploiement.md`](docs/deploiement.md).

---

## Documentation complémentaire

- [`docs/tvf_mapping.md`](docs/tvf_mapping.md) — Cartographie complète TVFs ↔ API ↔ colonnes JSON
- [`docs/deploiement.md`](docs/deploiement.md) — Procédure de build et déploiement Docker
