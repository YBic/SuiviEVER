"""
smoke_test_v12_droits.py
Verification LECTURE SEULE des droits confirmes par Nicolas le 2026-08-20 (§4.7, §4.8) :
  - SUPERVISEUR_ST gagne l'acces a Enqueteurs / Vacations Zone
  - SUPERVISEUR_IFOP et SUPERVISEUR_ST voient l'ecran Affectation (lecture) mais
    ne peuvent pas modifier une affectation
  - ROLE_HOME correct par role (page d'accueil §4.7)
  - Les nouveaux champs CSV (matricule/nom/prenom separes) sont bien exposes

Aucune ecriture. Session simulee (pas de mot de passe manipule).

Usage :
  python scripts/smoke_test_v12_droits.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ever_project.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from django.test import Client
from accounts.roles import ROLE_HOME

client = Client()


def seed_session(role, login='TEST_SMOKE', code_st='IFOP', id_st=None):
    session = client.session
    session['user_login']               = login
    session['user_role']                = role
    session['user_nom']                 = 'Test Smoke'
    session['user_role_label']          = role
    session['user_code_societe_terrain'] = code_st
    session['user_id_societe_terrain']  = id_st
    session['user_matricule']           = login
    session.save()


def check(label, resp, expect_status=200):
    ok = resp.status_code == expect_status
    print(f"{'OK ' if ok else 'FAIL'} [{resp.status_code}, attendu {expect_status}] {label}")
    if not ok:
        print('     body:', resp.content[:300])
    return ok


print('=' * 70)
print('ROLE_HOME (specs §4.7)')
print('=' * 70)
attendu = {
    'ADMIN_IFOP': 'core:suivi_aeroport',
    'RESPONSABLE_IFOP': 'core:suivi_aeroport',
    'RESPONSABLE_ST': 'core:suivi_hors_aeroport',
    'SUPERVISEUR_IFOP': 'core:suivi_aeroport',
    'SUPERVISEUR_ST': 'core:suivi_hors_aeroport',
    'ENQUETEUR': 'core:suivi_aeroport',
}
for role, expected in attendu.items():
    actual = ROLE_HOME.get(role)
    ok = actual == expected
    print(f"{'OK ' if ok else 'FAIL'} {role:20s} -> {actual} (attendu {expected})")

print('\n' + '=' * 70)
print('SUPERVISEUR_ST — retire des 3 menus v1.1 au call du 21/08 (doit etre refuse)')
print('=' * 70)
seed_session('SUPERVISEUR_ST', code_st='SOLUTION_TERRAIN', id_st=2)
check('GET /enqueteurs/ (302, refuse)', client.get('/enqueteurs/'), expect_status=302)
check('GET /vacations-zone/ (302, refuse)', client.get('/vacations-zone/'), expect_status=302)

print('\n' + '=' * 70)
print('RESPONSABLE_ST — garde Enqueteurs / Vacations Zone')
print('=' * 70)
seed_session('RESPONSABLE_ST', code_st='SOLUTION_TERRAIN', id_st=2)
check('GET /enqueteurs/', client.get('/enqueteurs/'))
check('GET /vacations-zone/', client.get('/vacations-zone/'))
r = client.get('/api/vacations-zone/', {'date_debut': '2026-06-01', 'date_fin': '2026-06-30'})
check('GET /api/vacations-zone/', r)
if r.status_code == 200:
    data = r.json().get('data', [])
    print(f'     -> {len(data)} vacations sur juin 2026')
    if data:
        keys = ('ID_Zone_Enquete', 'Matricule_Enqueteur_1', 'Nom_Enqueteur_1', 'Prenom_Enqueteur_1')
        missing = [k for k in keys if k not in data[0]]
        print(f"     -> champs CSV presents : {'OK' if not missing else 'MANQUANT ' + str(missing)}")

r_enq = client.get('/api/enqueteurs-terrain/')
check('GET /api/enqueteurs-terrain/ (champs blocage/fin mission)', r_enq)
if r_enq.status_code == 200:
    d = r_enq.json().get('data', [])
    if d:
        keys = ('Date_Fin_Mission', 'Date_Blocage_IFOP_Affectation', 'Motif_Blocage_IFOP_Affectation')
        missing = [k for k in keys if k not in d[0]]
        print(f"     -> champs presents : {'OK' if not missing else 'MANQUANT ' + str(missing)}")

print('\n' + '=' * 70)
print('SUPERVISEUR_IFOP — Affectation : VOIR oui, MODIFIER non')
print('=' * 70)
seed_session('SUPERVISEUR_IFOP', code_st='IFOP', id_st=None)
r_page = client.get('/affectation/')
check('GET /affectation/ (doit etre 200, avant : 302)', r_page)
if r_page.status_code == 200 and b'CAN_MODIFY_AFFECTATION' in r_page.content:
    idx = r_page.content.find(b'CAN_MODIFY_AFFECTATION')
    snippet = r_page.content[idx:idx+40]
    print('     ->', snippet)
    if b'false' in snippet:
        print('     OK : CAN_MODIFY_AFFECTATION = false (lecture seule)')
    else:
        print('     FAIL : devrait etre false pour un superviseur')

check('GET /api/affectation/vacations/ (doit etre 200, lecture)',
      client.get('/api/affectation/vacations/', {'date': '2026-06-01'}))
check('POST /api/affectation/set/ (doit etre refuse, 403)',
      client.post('/api/affectation/set/', data='{"id_vacation":1,"id_personne":null,"type":"AEROPORT"}',
                   content_type='application/json'),
      expect_status=403)

print('\n' + '=' * 70)
print('ADMIN_IFOP — Affectation : VOIR et MODIFIER')
print('=' * 70)
seed_session('ADMIN_IFOP', login='BICREL_Y', code_st='IFOP', id_st=None)
r_page = client.get('/affectation/')
check('GET /affectation/', r_page)
if b'CAN_MODIFY_AFFECTATION' in r_page.content:
    idx = r_page.content.find(b'CAN_MODIFY_AFFECTATION')
    print('     ->', r_page.content[idx:idx+40])

print('\n' + '=' * 70)
print('ENQUETEUR — toujours refuse partout (inchange)')
print('=' * 70)
seed_session('ENQUETEUR', code_st='SOLUTION_TERRAIN', id_st=2)
check('GET /affectation/ (302)', client.get('/affectation/'), expect_status=302)
check('GET /enqueteurs/ (302)', client.get('/enqueteurs/'), expect_status=302)
check('GET /vacations-zone/ (302)', client.get('/vacations-zone/'), expect_status=302)

print('\nTermine.')
