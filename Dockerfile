# ── Image de base ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── Drivers ODBC Microsoft pour SQL Server (Debian 12 / bookworm) ──────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,armhf,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get purge -y --auto-remove curl gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Dépendances Python ──────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Code applicatif ─────────────────────────────────────────────────────────────
# (le .dockerignore exclut .env, debug_login.py, sessions/, logs/, .git, etc.)
COPY . .

# ── Fichiers statiques (whitenoise les sert directement) ───────────────────────
# DEBUG forcé à False : pas de dépendance aux env vars de runtime au build.
RUN DEBUG=False SECRET_KEY=build-only python manage.py collectstatic --noinput

# ── Répertoires persistants (montés en volume dans docker-compose) ──────────────
RUN mkdir -p /app/logs /app/sessions

# ── Utilisateur non-root ────────────────────────────────────────────────────────
RUN useradd --create-home --uid 10001 ever \
    && chown -R ever:ever /app
USER ever

EXPOSE 8000

# ── Démarrage : gunicorn, 3 workers, timeout 120s ──────────────────────────────
CMD ["gunicorn", "ever_project.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile",  "-"]
