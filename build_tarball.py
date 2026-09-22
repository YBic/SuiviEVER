"""
build_tarball.py — Crée le tarball de déploiement pour Portainer Upload.
Usage : python build_tarball.py
Sortie : ../suivi-ever.tar.gz  (Dockerfile à la racine de l'archive)
"""
import tarfile
import os
import sys

EXCLUDE = {
    '.git', '__pycache__', '.env', 'staticfiles',
    '.venv', 'venv', 'suivi-ever.tar.gz', 'build_tarball.py',
}
OUTPUT = '../suivi-ever.tar.gz'

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    entries = [n for n in os.listdir('.') if n not in EXCLUDE and not n.endswith('.tar.gz')]

    out_path = os.path.abspath(OUTPUT)
    with tarfile.open(out_path, 'w:gz') as t:
        for name in sorted(entries):
            t.add(name)
            print(f'  + {name}')

    print(f'\nTarball créé : {out_path}')

    # Vérification rapide
    EXPECTED = [
        'Dockerfile',
        'static/img/favicon.svg',
        'static/js/ever.js',
        'static/css/ever.css',
        'core/templates/core/base.html',
    ]
    with tarfile.open(out_path) as t:
        names = t.getnames()
    ok = True
    for exp in EXPECTED:
        found = any(exp in n for n in names)
        print(f"{'OK' if found else 'MANQUANT'} — {exp}")
        if not found:
            ok = False

    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
