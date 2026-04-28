# deploy.ps1 — Build, push et déploiement de l'image EVER sur srv-dbapps-01
#
# Prérequis :
#   - Docker Desktop installé sur ce PC
#   - Accès SSH au serveur (ssh yann_bicrel@10.100.1.117)
#   - Le registry interne est accessible via le tunnel SSH (voir ci-dessous)
#
# Usage : .\deploy.ps1 [-Tag "1.0.0"]

param(
    [string]$Tag = "latest"
)

$REGISTRY  = "localhost:5000"
$IMAGE     = "ever-suivi"
$SERVER    = "10.100.1.117"
$SSH_USER  = "yann_bicrel"           # à adapter si différent
$FULL_TAG  = "${REGISTRY}/${IMAGE}:${Tag}"

Write-Host "=== EVER Deploy — tag: $Tag ===" -ForegroundColor Cyan

# ── 1. Build de l'image ────────────────────────────────────────────────────────
Write-Host "`n[1/3] Build de l'image Docker..." -ForegroundColor Yellow
docker build -t $FULL_TAG .
if ($LASTEXITCODE -ne 0) { Write-Host "ERREUR : build échoué" -ForegroundColor Red; exit 1 }

# ── 2. Push via tunnel SSH ─────────────────────────────────────────────────────
# Le registry écoute sur localhost:5000 côté serveur.
# On ouvre un tunnel SSH : localhost:5000 → serveur:5000, on pousse, on ferme.
Write-Host "`n[2/3] Push de l'image vers le registry interne..." -ForegroundColor Yellow
Write-Host "  → Ouverture du tunnel SSH (localhost:5000 → ${SERVER}:5000)"

$tunnel = Start-Process ssh -ArgumentList "-N -L 5000:localhost:5000 ${SSH_USER}@${SERVER}" -PassThru
Start-Sleep -Seconds 3   # laisser le tunnel s'établir

# Indiquer à Docker que ce registry local est non-HTTPS (insecure)
# (à faire une seule fois : ajouter {"insecure-registries":["localhost:5000"]} dans Docker Desktop → Settings → Docker Engine)
docker push $FULL_TAG
$pushOk = $LASTEXITCODE

$tunnel | Stop-Process -Force
if ($pushOk -ne 0) { Write-Host "ERREUR : push échoué" -ForegroundColor Red; exit 1 }

# ── 3. Redémarrage du stack via SSH ───────────────────────────────────────────
Write-Host "`n[3/3] Mise à jour du stack sur le serveur..." -ForegroundColor Yellow
ssh "${SSH_USER}@${SERVER}" "docker pull $FULL_TAG && docker stack deploy -c /opt/stacks/ever/docker-compose.yml ever --with-registry-auth"

Write-Host "`n=== Déploiement terminé ===" -ForegroundColor Green
Write-Host "  Site : https://ever.ifop.com"
