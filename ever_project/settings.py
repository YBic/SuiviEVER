from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ever_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ever_project.wsgi.application'

# Pas d'ORM Django : accès direct SQL Server via pyodbc
DATABASES = {}

# Sessions stockées côté serveur en fichiers
SESSION_ENGINE   = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = os.getenv('SESSION_FILE_PATH', BASE_DIR / 'sessions')
SESSION_COOKIE_AGE = 3600  # 1 heure
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# En production derrière NPM (HTTPS), sécuriser le cookie de session
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# Indique à Django qu'il est derrière un reverse proxy HTTPS (nginx-proxy-manager)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Connexion SQL Server (pyodbc)
DB_CONNECTION = {
    'DRIVER': '{ODBC Driver 17 for SQL Server}',
    'SERVER': os.getenv('DB_HOST', r'localhost\SQLEXPRESS'),
    'DATABASE': os.getenv('DB_NAME', 'EVER_2026'),
    'UID': os.getenv('DB_USER', ''),
    'PWD': os.getenv('DB_PASSWORD', ''),
    'TrustServerCertificate': 'yes',
}

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme')

# Mot de passe générique accepté uniquement pour les comptes sans mot de passe (première connexion)
FIRST_LOGIN_PASSWORD = os.getenv('FIRST_LOGIN_PASSWORD', 'Ever@2026')

LOGIN_URL = '/login/'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'ever': {
            'format':  '{asctime} {levelname:<8} [{name}] {message}',
            'style':   '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'ever',
        },
        'file_auth': {
            'class':       'logging.handlers.RotatingFileHandler',
            'filename':    LOGS_DIR / 'auth.log',
            'maxBytes':    5 * 1024 * 1024,
            'backupCount': 10,
            'formatter':   'ever',
            'encoding':    'utf-8',
        },
        'file_app': {
            'class':       'logging.handlers.RotatingFileHandler',
            'filename':    LOGS_DIR / 'app.log',
            'maxBytes':    5 * 1024 * 1024,
            'backupCount': 10,
            'formatter':   'ever',
            'encoding':    'utf-8',
        },
    },

    'loggers': {
        # Événements d'authentification (login, set_password, logout)
        'ever.auth': {
            'handlers':  ['console', 'file_auth'],
            'level':     'INFO',
            'propagate': False,
        },
        # Erreurs SQL dans la couche db
        'ever.db': {
            'handlers':  ['console', 'file_app'],
            'level':     'WARNING',
            'propagate': False,
        },
    },
}
