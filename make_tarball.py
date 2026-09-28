"""
make_tarball.py — Génère l'archive de build à uploader dans Portainer.

Usage :
    python make_tarball.py

Produit `ever-suivi-build.tar.gz` à la racine. Cette archive contient le
Dockerfile + le code applicatif ; c'est le serveur (via Portainer → Images →
Build → Upload) qui construit l'image. Aucun Docker requis sur le poste dev.

Les exclusions ci-dessous restent cohérentes avec .dockerignore : on évite
d'embarquer les secrets (.env), les scripts de diagnostic, les artefacts
locaux (staticfiles régénéré au build, sessions, logs) et les caches.
"""
import tarfile
import pathlib

OUT = pathlib.Path('ever-suivi-build.tar.gz')

# Dossiers/fichiers à NE PAS inclure dans le contexte de build
SKIP_PARTS = {
    '.git', '.venv', 'venv', 'env', '__pycache__',
    'staticfiles', 'sessions', 'logs',
    '.vscode', '.idea',
    '_diag',    # dumps du code source d'objets SQL IFOP, dont la fonction
                # d'authentification : rien à faire dans l'image applicative
}
SKIP_NAMES = {
    '.env',                      # secrets : la config prod est dans Portainer
    'debug_login.py',            # script de diagnostic
    '.DS_Store', 'Thumbs.db',
}
SKIP_SUFFIXES = {'.pyc', '.pyo', '.swp', '.gz'}   # .gz : les archives de build,
                                                  # dont celle produite ici


def keep(p: pathlib.Path) -> bool:
    if any(part in SKIP_PARTS for part in p.parts):
        return False
    if p.name in SKIP_NAMES:
        return False
    if p.suffix in SKIP_SUFFIXES:
        return False
    return True


def main():
    root = pathlib.Path('.')
    count = 0
    with tarfile.open(OUT, 'w:gz') as tf:
        for p in sorted(root.rglob('*')):
            if not p.is_file():
                continue
            if not keep(p):
                continue
            tf.add(p, arcname=str(p.relative_to(root)))
            count += 1
    size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"OK : {OUT} ({count} fichiers, {size_mb:.1f} Mo)")
    print("→ Portainer → Images → Build a new image → Upload → ce fichier")


if __name__ == '__main__':
    main()
