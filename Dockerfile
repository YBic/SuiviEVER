# ── Image de base ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

# ── Drivers ODBC Microsoft pour SQL Server (Debian 12 / bookworm) ──────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/12/prod.list \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Dépendances Python ──────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Code applicatif ─────────────────────────────────────────────────────────────
COPY . .

# ── Fichiers statiques (whitenoise les sert directement) ───────────────────────
RUN python manage.py collectstatic --noinput

# ── Répertoires persistants (montés en volume dans docker-compose) ──────────────
RUN mkdir -p /app/logs /app/sessions

EXPOSE 8000

# ── Démarrage : gunicorn, 3 workers, timeout 120s ──────────────────────────────
CMD ["gunicorn", "ever_project.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "/app/logs/gunicorn-access.log", \
     "--error-logfile",  "/app/logs/gunicorn-error.log"]
