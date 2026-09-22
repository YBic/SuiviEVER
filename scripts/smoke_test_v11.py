"""
smoke_test_v11.py
Verification de bout en bout des nouveaux ecrans v1.1 (Enqueteurs, Vacations Zone)
via le client de test Django — session simulee (pas de vrai login, pas de mot
de passe manipule), requetes reelles contre EVER_EXP (lecture seule sauf la
section CREATION explicitement marquee, qui nettoie ensuite ce qu'elle a cree).

Usage :
  python scripts/smoke_test_v11.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ever_project.settings')
django.setup()

from django.conf import settings
# Autorise le host du client de test Django pour ce process uniquement
# (ne touche pas au .env / ALLOWED_HOSTS persistant).
settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from django.test import Client

client = Client()


def seed_session(role='ADMIN_IFOP', login='BICREL_Y', code_st='IFOP', id_st=None):
    session = client.session
    session['user_login']                   = login
    session['user_role']                     = role
    session['user_nom']                      = 'Test Smoke'
    session['user_role_label']               = role
    session['user_code_societe_terrain']     = code_st
    session['user_id_societe_terrain']       = id_st
    session['user_matricule']                = login
    session.save()


def check(label, resp, expect_status=200):
    ok = resp.status_code == expect_status
    print(f"{'OK ' if ok else 'FAIL'} [{resp.status_code}] {label}")
    if not ok:
        print('     body:', resp.content[:300])
    return ok


print('=' * 70)
print('SMOKE TEST v1.1 — session ADMIN_IFOP (BICREL_Y)')
print('=' * 70)
seed_session(role='ADMIN_IFOP', login='BICREL_Y', code_st='IFOP', id_st=None)

r = check('GET /enqueteurs/', client.get('/enqueteurs/'))
r = check('GET /vacations-zone/', client.get('/vacations-zone/'))

r = client.get('/api/enqueteurs-terrain/')
check('GET /api/enqueteurs-terrain/', r)
if r.status_code == 200:
    data = r.json()
    print(f"     -> {len(data.get('data', []))} enqueteurs, status={data.get('status')}")
    if data['data']:
        print('     -> exemple :', data['data'][0])

r = client.get('/api/zones-enquete/')
check('GET /api/zones-enquete/', r)
if r.status_code == 200:
    zdata = r.json()
    print(f"     -> {len(zdata.get('data', []))} zones")

r = client.get('/api/vacations-zone/', {'date_debut': '2026-06-01', 'date_fin': '2026-06-01'})
check('GET /api/vacations-zone/ (2026-06-01)', r)
if r.status_code == 200:
    vdata = r.json()
    print(f"     -> {len(vdata.get('data', []))} vacations, status={vdata.get('status')}")
    if vdata['data']:
        print('     -> exemple :', vdata['data'][0])
        premiere_vac = vdata['data'][0]
        id_vac = premiere_vac.get('ID_Vacation_Zone_1')
        if id_vac:
            rd = client.get('/api/vacations-zone/detail/', {'id_vacation': id_vac})
            check(f'GET /api/vacations-zone/detail/ (id={id_vac})', rd)
            if rd.status_code == 200:
                ddata = rd.json()
                print(f"     -> {len(ddata.get('data', []))} sites")

print('\n' + '=' * 70)
print('SMOKE TEST v1.1 — session RESPONSABLE_ST (test, societe=2)')
print('=' * 70)
seed_session(role='RESPONSABLE_ST', login='TEST_ST_SMOKE', code_st='SOLUTION_TERRAIN', id_st=2)
check('GET /enqueteurs/ (RESPONSABLE_ST)', client.get('/enqueteurs/'))
check('GET /vacations-zone/ (RESPONSABLE_ST)', client.get('/vacations-zone/'))

print('\n' + '=' * 70)
print('SMOKE TEST v1.1 — droits refuses (ENQUETEUR)')
print('=' * 70)
seed_session(role='ENQUETEUR', login='TEST_ENQ_SMOKE', code_st='SOLUTION_TERRAIN', id_st=2)
check('GET /enqueteurs/ (ENQUETEUR, doit rediriger 302)', client.get('/enqueteurs/'), expect_status=302)
check('GET /vacations-zone/ (ENQUETEUR, doit rediriger 302)', client.get('/vacations-zone/'), expect_status=302)
check('GET /api/enqueteurs-terrain/ (ENQUETEUR, doit refuser 403)', client.get('/api/enqueteurs-terrain/'), expect_status=403)

print('\n' + '=' * 70)
print('SMOKE TEST v1.1 — CREATION reelle (EVER_DEV, date jetable 2028-01-15, ANNEMASSE)')
print('=' * 70)
seed_session(role='ADMIN_IFOP', login='BICREL_Y', code_st='IFOP', id_st=None)

import json as _json
TEST_DATE = '2026-09-25'   # dans la fenetre autorisee (<= 27/09/2026), inoccupee

import pyodbc
_pre = pyodbc.connect(
    r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=SRV-LANSQL-03\MSSQLIFOPGE;'
    r'DATABASE=EVER_DEV;Trusted_Connection=yes;TrustServerCertificate=yes;', timeout=15)
_cur = _pre.cursor()
_cur.execute("SELECT COUNT(*) FROM dbo.Vacation_Zone WHERE Date_Vacation=? AND ID_Zone_Enquete=19", (TEST_DATE,))
print(f'     -> vacations existantes le {TEST_DATE} zone 19 avant test (doit etre 0):', _cur.fetchone())
_pre.close()

payload = {'lignes': [{'date_vacation': TEST_DATE, 'id_zone_enquete': 19}]}
r = client.post('/api/vacations-zone/create/', data=_json.dumps(payload), content_type='application/json')
check('POST /api/vacations-zone/create/', r)
print('     body:', r.content[:300])

r2 = client.get('/api/vacations-zone/', {'date_debut': TEST_DATE, 'date_fin': TEST_DATE, 'id_zone_enquete': 19})
if r2.status_code == 200:
    vdata = r2.json()
    print(f"     -> relecture : {len(vdata.get('data', []))} vacation(s) creee(s)")
    for v in vdata.get('data', []):
        print('        ', v)

# Nettoyage : suppression de la vacation de test (EVER_DEV, dev local)
conn = pyodbc.connect(
    r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=SRV-LANSQL-03\MSSQLIFOPGE;'
    r'DATABASE=EVER_DEV;Trusted_Connection=yes;TrustServerCertificate=yes;', timeout=15)
cur = conn.cursor()
cur.execute("SELECT ID_Vacation_Zone FROM dbo.Vacation_Zone WHERE Date_Vacation=? AND ID_Zone_Enquete=19", (TEST_DATE,))
ids = [row[0] for row in cur.fetchall()]
print(f'     -> nettoyage : suppression de {len(ids)} ligne(s) Vacation_Zone/Vacation_Zone_Site de test')
for vid in ids:
    cur.execute("DELETE FROM dbo.Vacation_Zone_Site WHERE ID_Vacation_Zone=?", (vid,))
    cur.execute("DELETE FROM dbo.Vacation_Zone WHERE ID_Vacation_Zone=?", (vid,))
conn.commit()
cur.execute("SELECT COUNT(*) FROM dbo.Vacation_Zone WHERE Date_Vacation=?", (TEST_DATE,))
print('     -> verification post-nettoyage (doit etre 0):', cur.fetchone())
conn.close()

print('\nTermine.')
