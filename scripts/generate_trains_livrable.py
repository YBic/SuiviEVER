"""
generate_trains_livrable.py
Génère le livrable de programmes de trains internationaux pour import Philippe.
Format de sortie : colonnes de Fichier_Train_Tmp (SQL Server EVER).
Filtre : dates du 2026-07-01 au 2026-09-30.

Sources traitées :
  - SNCF          (Export_OpenData_SNCF_GTFS_NewTripId)
  - EUROSTAR       (gtfs_static_commercial_v2)
  - RENFE          (Renfe_AVE_Int)
  - TRENITALIA     (Trenitalia gtfs)

Usage :
  python scripts/generate_trains_livrable.py
"""

import csv
import io
import os
import re
import sys
import zipfile
from collections import defaultdict

import openpyxl
import pandas as pd
import pyodbc

# ── Paramètres ────────────────────────────────────────────────────────────────
GTFS_DIR  = r'Z:\Transfert Info\Nicolas\EVER_2026\9_Programme_trains'
OUTPUT    = r'C:\Users\y_bicrel\Downloads\EVER_Programmes_trains_sept_oct_nov_20260914.xlsx'
DATE_MIN  = '20260901'
DATE_MAX  = '20261130'

SOURCES = {
    'SNCF':       '20260914_Export_OpenData_SNCF_GTFS_NewTripId (8).zip',
    'EUROSTAR':   '20260914_gtfs_static_commercial_v2 (4).zip',
    'RENFE':      '20260914_Renfe_AVE_Int (3).zip',
    'TRENITALIA': '20260914_Trenitalia gtfs.zip',
}

# Boîtes englobantes pays (lat_min, lon_min, lat_max, lon_max)
# Ordre important : MC, LU avant FR/DE/BE/CH pour éviter ambiguïtés
COUNTRY_BOXES = [
    ('MC', 43.72, 7.38, 43.77, 7.44),
    ('LU', 49.44, 5.73, 50.18, 6.53),
    ('GB', 49.9, -8.2, 61.0, 2.0),
    ('BE', 49.5, 2.5, 51.5, 6.4),
    ('NL', 50.7, 3.3, 53.6, 7.3),
    ('CH', 45.8, 5.9, 47.8, 10.5),
    ('AT', 46.4, 9.5, 49.0, 17.2),
    ('IT', 35.5, 6.6, 47.1, 18.5),
    ('ES', 35.9, -9.3, 43.8, 3.5),
    ('DE', 47.3, 5.8, 55.1, 15.1),
    ('FR', 41.3, -5.2, 51.2, 9.6),
]

def detect_country_by_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return 'XX'
    for iso2, lat_min, lon_min, lat_max, lon_max in COUNTRY_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return iso2
    return 'XX'

# ── Chargement mapping DB ──────────────────────────────────────────────────────
def load_db_stop_mapping():
    """
    Retourne deux dicts :
      stop_to_country : {(source_code, code_gare_db): iso2}
        ex: ('SNCF', '87212027') -> 'FR'
            ('SNCF', 'BARCELONE_SANTS') -> 'ES'
      stop_to_name    : {(source_code, code_gare_db): nom_gare_ifop}
    """
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=SRV-LANSQL-03\\MSSQLIFOPGE;'
        'DATABASE=EVER_DEV;'
        'Trusted_Connection=yes;'
    )
    cur = conn.cursor()
    cur.execute('''
        SELECT sdg.Code_Source_Donnee_Train,
               sdg.Code_Gare,
               sdg.Libelle_Gare,
               p.Code_Pays_ISO_2
        FROM Source_Donnee_Train_Gare sdg
        LEFT JOIN Gare_Train g ON g.ID_Gare_Train = sdg.ID_Gare_Train
        LEFT JOIN Pays_ISO   p ON p.ID_Pays_ISO   = g.ID_Pays_ISO
    ''')
    stop_to_country = {}
    stop_to_name    = {}
    for source, code, libelle, iso2 in cur.fetchall():
        k = (source.strip(), code.strip())
        stop_to_country[k] = (iso2 or 'XX').strip()
        stop_to_name[k]    = libelle.strip() if libelle else ''
    conn.close()
    return stop_to_country, stop_to_name


# ── Lecture GTFS helpers ───────────────────────────────────────────────────────
def gtfs_read(zf, filename, usecols=None):
    """Lit un fichier GTFS depuis un ZipFile et renvoie un DataFrame pandas."""
    with zf.open(filename) as f:
        df = pd.read_csv(
            io.TextIOWrapper(f, encoding='utf-8-sig'),
            dtype=str,
            low_memory=False,
        )
    # Strip whitespace from column names (RENFE has trailing spaces)
    df.columns = [c.strip() for c in df.columns]
    # Strip whitespace from values
    for col in df.columns:
        df[col] = df[col].str.strip() if df[col].dtype == object else df[col]
    if usecols:
        # Only keep requested columns that exist
        existing = [c for c in usecols if c in df.columns]
        df = df[existing]
    return df


def dates_in_range(service_dates: dict, service_id: str) -> list:
    """Retourne les dates (format YYYYMMDD) dans [DATE_MIN, DATE_MAX] pour un service_id."""
    dates = service_dates.get(service_id, [])
    return sorted(d for d in dates if DATE_MIN <= d <= DATE_MAX)


# ── Utilitaires SNCF ──────────────────────────────────────────────────────────
_RE_SNCF_CODE = re.compile(r'-(\d{8})$')

def sncf_extract_uic(stop_id: str) -> str:
    """Extrait le code UIC (8 chiffres) d'un stop_id SNCF. Retourne '' sinon."""
    m = _RE_SNCF_CODE.search(stop_id)
    return m.group(1) if m else ''

def sncf_extract_text_code(stop_id: str) -> str:
    """
    Pour les gares étrangères SNCF dont le stop_id est de la forme
    StopPoint:OCELyria-GENEVE_CORNAVIN : extrait la partie après le dernier '-'
    si ce n'est pas un code numérique.
    """
    part = stop_id.rsplit('-', 1)[-1] if '-' in stop_id else stop_id
    if re.match(r'^\d{8}$', part):
        return ''   # c'est un code UIC → traité par sncf_extract_uic
    return part     # ex: 'GENEVE_CORNAVIN', 'BARCELONE_SANTS', etc.


def sncf_get_country(stop_id, stop_lat, stop_lon, s2c):
    """Retourne (code_gare_db, iso2) pour un stop SNCF."""
    uic = sncf_extract_uic(stop_id)
    if uic:
        key = ('SNCF', uic)
        if key in s2c:
            return uic, s2c[key]
        # UIC commençant par 87 = France
        if uic.startswith('87'):
            return uic, 'FR'
        return uic, detect_country_by_coords(stop_lat, stop_lon)
    txt = sncf_extract_text_code(stop_id)
    if txt:
        key = ('SNCF', txt)
        if key in s2c:
            return txt, s2c[key]
    return '', detect_country_by_coords(stop_lat, stop_lon)


# ── Traitement générique ───────────────────────────────────────────────────────
def build_rows_from_gtfs(source_name, zf, fr_stop_ids, stop_country, stop_name_map,
                         service_dates, stop_name_by_id):
    """
    Génère les lignes du livrable pour un source GTFS.

    fr_stop_ids  : set des stop_ids qui sont des gares françaises
    stop_country : dict {stop_id: iso2}
    stop_name_map: dict {stop_id: nom affiché}
    service_dates: dict {service_id: [list of YYYYMMDD]}
    stop_name_by_id: dict {stop_id: nom}

    Retourne une liste de dicts (colonnes Fichier_Train_Tmp).
    """
    print(f'  Chargement stop_times ({source_name})...')
    st = gtfs_read(zf, 'stop_times.txt',
                   usecols=['trip_id', 'stop_id', 'stop_sequence',
                             'arrival_time', 'departure_time'])
    st['stop_sequence'] = pd.to_numeric(st['stop_sequence'], errors='coerce').fillna(0).astype(int)

    print(f'  Chargement trips ({source_name})...')
    trips = gtfs_read(zf, 'trips.txt',
                      usecols=['trip_id', 'service_id', 'route_id'])

    # Limite : uniquement les trips qui ont au moins un arrêt FR
    fr_trip_ids = set(st.loc[st['stop_id'].isin(fr_stop_ids), 'trip_id'])
    print(f'    {len(fr_trip_ids)} trips passant par une gare FR')

    if not fr_trip_ids:
        return []

    st_fr_trips = st[st['trip_id'].isin(fr_trip_ids)].copy()

    # Pour chaque trip : liste ordonnée des arrêts
    grouped = st_fr_trips.sort_values('stop_sequence').groupby('trip_id')

    trip_meta = trips.set_index('trip_id')

    rows = []
    total = len(fr_trip_ids)
    print(f'  Traitement de {total} trips...')

    for i, (trip_id, grp) in enumerate(grouped):
        if i % 10000 == 0:
            print(f'    {i}/{total}', end='\r')

        stop_ids_ordered = grp['stop_id'].tolist()
        stop_seqs        = grp['stop_sequence'].tolist()
        arrivals         = grp['arrival_time'].tolist()
        departures       = grp['departure_time'].tolist()

        # Pays de chaque arrêt
        countries = [stop_country.get(s, 'XX') for s in stop_ids_ordered]

        # Vérifier qu'il y a au moins un arrêt étranger (non FR)
        has_foreign = any(c != 'FR' and c != 'XX' for c in countries)
        if not has_foreign:
            continue

        # Service_id et route_id
        try:
            meta = trip_meta.loc[trip_id]
            service_id = meta['service_id']
            route_id   = meta['route_id']
        except KeyError:
            continue

        # Dates dans la période [DATE_MIN, DATE_MAX]
        dates = dates_in_range(service_dates, service_id)
        if not dates:
            continue

        dates_str = ','.join(dates)

        # Départ et terminus du train
        gare_depart_id  = stop_ids_ordered[0]
        gare_terminus_id = stop_ids_ordered[-1]
        gare_depart_nom  = stop_name_by_id.get(gare_depart_id, gare_depart_id)
        gare_terminus_nom = stop_name_by_id.get(gare_terminus_id, gare_terminus_id)
        pays_terminus = stop_country.get(gare_terminus_id, 'XX')

        # Pays étrangers et gares étrangères sur le trajet
        foreign_countries = sorted(set(
            c for c in countries if c not in ('FR', 'XX')
        ))
        foreign_stations = list(dict.fromkeys(
            stop_name_by_id.get(s, s)
            for s, c in zip(stop_ids_ordered, countries)
            if c not in ('FR', 'XX')
        ))
        pays_etrangers_str = ','.join(foreign_countries)
        gares_etrangeres_str = ','.join(foreign_stations)

        # Une ligne par arrêt français
        for stop_id, seq, arr, dep, country in zip(
            stop_ids_ordered, stop_seqs, arrivals, departures, countries
        ):
            if country != 'FR':
                continue
            if stop_id not in fr_stop_ids:
                continue

            rows.append({
                'Source_Donnee':              source_name,
                'Code_Gare_Source':           stop_id,
                'Gare_Francaise':             stop_name_map.get(stop_id, stop_name_by_id.get(stop_id, stop_id)),
                'ID_Trajet':                  trip_id,
                'ID_Service':                 service_id,
                'ID_Ligne':                   route_id,
                'Ordre_Arret':                str(seq),
                'Heure_Arrivee':              arr or '',
                'Heure_Depart':               dep or '',
                'Gare_Depart':                gare_depart_nom,
                'Gare_Terminus':              gare_terminus_nom,
                'Pays_Terminus':              pays_terminus,
                'Pays_Etrangers_Detectes':    pays_etrangers_str,
                'Gares_Etrangeres_Detectees': gares_etrangeres_str[:2000],
                'Premieres_Dates_Circulation': dates_str[:1000],
            })

    print(f'    {total}/{total} — {len(rows)} lignes générées')
    return rows


# ── Chargement calendar_dates (+ calendar.txt si présent) ─────────────────────
def load_service_dates(zf):
    """Retourne {service_id: [YYYYMMDD, ...]} pour dates dans [DATE_MIN, DATE_MAX]."""
    service_dates = defaultdict(list)

    if 'calendar.txt' in zf.namelist():
        cal = gtfs_read(zf, 'calendar.txt')
        # Génère toutes les dates entre start_date et end_date selon les jours
        import datetime
        day_cols = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        for _, row in cal.iterrows():
            try:
                start = datetime.datetime.strptime(row['start_date'], '%Y%m%d').date()
                end   = datetime.datetime.strptime(row['end_date'], '%Y%m%d').date()
            except Exception:
                continue
            service_id = row['service_id']
            days_active = [int(row.get(d, 0) or 0) for d in day_cols]
            cur = start
            while cur <= end:
                yyyymmdd = cur.strftime('%Y%m%d')
                if DATE_MIN <= yyyymmdd <= DATE_MAX and days_active[cur.weekday()]:
                    service_dates[service_id].append(yyyymmdd)
                cur += datetime.timedelta(days=1)

    if 'calendar_dates.txt' in zf.namelist():
        cd = gtfs_read(zf, 'calendar_dates.txt',
                       usecols=['service_id', 'date', 'exception_type'])
        # Si exception_type absent (certains GTFS l'omettent), on l'ajoute par défaut à 1
        if 'exception_type' not in cd.columns:
            cd['exception_type'] = '1'
        # exception_type 1 = ajout, 2 = suppression
        for _, row in cd.iterrows():
            d = row['date']
            if not (DATE_MIN <= d <= DATE_MAX):
                continue
            sid = row['service_id']
            etype = int(row.get('exception_type', 1) or 1)
            if etype == 1:
                if d not in service_dates[sid]:
                    service_dates[sid].append(d)
            elif etype == 2:
                if d in service_dates[sid]:
                    service_dates[sid].remove(d)

    return dict(service_dates)


# ── SNCF ──────────────────────────────────────────────────────────────────────
def process_sncf(zf, s2c, s2n):
    print('\n=== SNCF ===')
    stops = gtfs_read(zf, 'stops.txt',
                      usecols=['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'location_type'])
    # Garder uniquement les stop points (location_type == 0 ou vide)
    stops = stops[stops['location_type'].isin(['0', ''])]

    # Construire stop_country et stop_name_by_id
    stop_country   = {}
    stop_name_by_id = {}
    fr_stop_ids     = set()
    stop_name_map   = {}   # stop_id -> Gare_Francaise (nom IFOP si dispo)

    for _, row in stops.iterrows():
        sid  = row['stop_id']
        name = row['stop_name']
        lat  = row.get('stop_lat', '')
        lon  = row.get('stop_lon', '')
        stop_name_by_id[sid] = name

        code_gare, iso2 = sncf_get_country(sid, lat, lon, s2c)
        stop_country[sid] = iso2

        if iso2 == 'FR':
            fr_stop_ids.add(sid)
            # Nom IFOP si disponible
            ifop_name = s2n.get(('SNCF', code_gare), '')
            stop_name_map[sid] = ifop_name if ifop_name else name

    print(f'  {len(fr_stop_ids)} gares françaises détectées')

    service_dates = load_service_dates(zf)
    print(f'  {len(service_dates)} service_ids avec dates en {DATE_MIN}-{DATE_MAX}')

    return build_rows_from_gtfs('SNCF', zf, fr_stop_ids, stop_country,
                                stop_name_map, service_dates, stop_name_by_id)


# ── EUROSTAR ──────────────────────────────────────────────────────────────────
_EUROSTAR_TZ_COUNTRY = {
    'Europe/Paris':     'FR',
    'Europe/Brussels':  'BE',
    'Europe/Amsterdam': 'NL',
    'Europe/London':    'GB',
    'Europe/Berlin':    'DE',
    'Europe/Madrid':    'ES',
    'Europe/Rome':      'IT',
    'Europe/Zurich':    'CH',
    'Europe/Luxembourg':'LU',
}

def process_eurostar(zf, s2c, s2n):
    print('\n=== EUROSTAR ===')
    stops = gtfs_read(zf, 'stops.txt')
    # Garder stop points (location_type == 0 ou vide)
    stops = stops[stops['location_type'].isin(['0', ''])]

    stop_country    = {}
    stop_name_by_id = {}
    fr_stop_ids     = set()
    stop_name_map   = {}

    for _, row in stops.iterrows():
        sid  = row['stop_id']
        name = row['stop_name']
        code = row.get('stop_code', '') or ''
        tz   = row.get('stop_timezone', '') or ''
        lat  = row.get('stop_lat', '')
        lon  = row.get('stop_lon', '')
        stop_name_by_id[sid] = name

        # Essai 1 : depuis la timezone
        iso2 = _EUROSTAR_TZ_COUNTRY.get(tz, '')
        # Essai 2 : DB par stop_code numérique
        if not iso2 and code:
            key = ('EUROSTAR', code)
            if key in s2c:
                iso2 = s2c[key]
        # Essai 3 : DB par slug uppercasé
        if not iso2:
            slug = sid.upper().replace('-', '_')
            key = ('EUROSTAR', slug)
            if key in s2c:
                iso2 = s2c[key]
        # Fallback coords
        if not iso2:
            iso2 = detect_country_by_coords(lat, lon)

        stop_country[sid] = iso2

        if iso2 == 'FR':
            fr_stop_ids.add(sid)
            # Nom IFOP : d'abord par stop_code, puis par slug
            ifop = ''
            if code:
                ifop = s2n.get(('EUROSTAR', code), '')
            if not ifop:
                slug = sid.upper().replace('-', '_')
                ifop = s2n.get(('EUROSTAR', slug), '')
            stop_name_map[sid] = ifop if ifop else name

    print(f'  {len(fr_stop_ids)} gares françaises détectées')

    service_dates = load_service_dates(zf)
    print(f'  {len(service_dates)} service_ids avec dates en {DATE_MIN}-{DATE_MAX}')

    return build_rows_from_gtfs('EUROSTAR', zf, fr_stop_ids, stop_country,
                                stop_name_map, service_dates, stop_name_by_id)


# ── RENFE ─────────────────────────────────────────────────────────────────────
def process_renfe(zf, s2c, s2n):
    print('\n=== RENFE ===')
    stops = gtfs_read(zf, 'stops.txt')
    # Garder uniquement les stops terminaux (location_type 0 ou vide)
    if 'location_type' in stops.columns:
        stops = stops[stops['location_type'].fillna('').isin(['0', ''])]

    stop_country    = {}
    stop_name_by_id = {}
    fr_stop_ids     = set()
    stop_name_map   = {}

    for _, row in stops.iterrows():
        sid  = str(row['stop_id']).strip()
        name = str(row.get('stop_name') or '').strip().replace('Estación de tren ', '')
        lat  = str(row.get('stop_lat') or '').strip()
        lon  = str(row.get('stop_lon') or '').strip()
        stop_name_by_id[sid] = name

        # RENFE utilise les codes UIC SNCF (87xxxxxx) pour les gares françaises
        if re.match(r'^87\d{3,}', sid):
            iso2 = 'FR'
        else:
            iso2 = detect_country_by_coords(lat, lon)
        stop_country[sid] = iso2

        if iso2 == 'FR':
            fr_stop_ids.add(sid)
            stop_name_map[sid] = name

    print(f'  {len(fr_stop_ids)} gares françaises détectées: {[stop_name_by_id[s] for s in fr_stop_ids]}')

    service_dates = load_service_dates(zf)
    print(f'  {len(service_dates)} service_ids avec dates en {DATE_MIN}-{DATE_MAX}')

    return build_rows_from_gtfs('RENFE', zf, fr_stop_ids, stop_country,
                                stop_name_map, service_dates, stop_name_by_id)


# ── TRENITALIA ────────────────────────────────────────────────────────────────
def process_trenitalia(zf, s2c, s2n):
    print('\n=== TRENITALIA ===')
    stops = gtfs_read(zf, 'stops.txt')

    # Les gares FR Trenitalia sont connues en DB : stop_id = numeric (10004-10008)
    fr_db_codes = {code for (src, code), _ in s2c.items() if src == 'TRENITALIA'
                   and s2c.get(('TRENITALIA', code)) == 'FR'}

    stop_country    = {}
    stop_name_by_id = {}
    fr_stop_ids     = set()
    stop_name_map   = {}

    for _, row in stops.iterrows():
        sid  = row['stop_id']
        name = row.get('stop_name', sid)
        lat  = row.get('stop_lat', '')
        lon  = row.get('stop_lon', '')
        stop_name_by_id[sid] = name

        # DB d'abord
        key = ('TRENITALIA', sid)
        if key in s2c:
            iso2 = s2c[key]
        else:
            iso2 = detect_country_by_coords(lat, lon)

        stop_country[sid] = iso2
        if iso2 == 'FR':
            fr_stop_ids.add(sid)
            ifop = s2n.get(('TRENITALIA', sid), '')
            stop_name_map[sid] = ifop if ifop else name

    print(f'  {len(fr_stop_ids)} gares françaises détectées: {[stop_name_by_id[s] for s in fr_stop_ids]}')

    service_dates = load_service_dates(zf)
    print(f'  {len(service_dates)} service_ids avec dates en {DATE_MIN}-{DATE_MAX}')

    return build_rows_from_gtfs('TRENITALIA', zf, fr_stop_ids, stop_country,
                                stop_name_map, service_dates, stop_name_by_id)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print('Chargement mapping DB...')
    s2c, s2n = load_db_stop_mapping()
    print(f'  {len(s2c)} correspondances stop → pays chargées')

    processors = {
        'SNCF':       process_sncf,
        'EUROSTAR':   process_eurostar,
        'RENFE':      process_renfe,
        'TRENITALIA': process_trenitalia,
    }

    all_rows = []
    for source_name, filename in SOURCES.items():
        path = os.path.join(GTFS_DIR, filename)
        if not os.path.exists(path):
            print(f'  ATTENTION : fichier introuvable : {path}')
            continue
        with zipfile.ZipFile(path) as zf:
            rows = processors[source_name](zf, s2c, s2n)
            all_rows.extend(rows)
            print(f'  → {len(rows)} lignes pour {source_name}')

    print(f'\nTotal : {len(all_rows)} lignes')

    if not all_rows:
        print('Aucune ligne générée. Vérifiez les fichiers GTFS et la période.')
        sys.exit(1)

    df = pd.DataFrame(all_rows, columns=[
        'Source_Donnee', 'Code_Gare_Source', 'Gare_Francaise',
        'ID_Trajet', 'ID_Service', 'ID_Ligne',
        'Ordre_Arret', 'Heure_Arrivee', 'Heure_Depart',
        'Gare_Depart', 'Gare_Terminus', 'Pays_Terminus',
        'Pays_Etrangers_Detectes', 'Gares_Etrangeres_Detectees',
        'Premieres_Dates_Circulation',
    ])

    print(f'\nÉcriture de {OUTPUT}...')
    with pd.ExcelWriter(OUTPUT, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Fichier_Train_Tmp', index=False)

        # Onglet de synthèse par source/gare
        summary = (df.groupby(['Source_Donnee', 'Gare_Francaise'])
                     .size()
                     .reset_index(name='Nbre_Trajets')
                     .sort_values(['Source_Donnee', 'Gare_Francaise']))
        summary.to_excel(writer, sheet_name='Synthese_Gares', index=False)

    print(f'Fichier écrit : {OUTPUT}')
    print(f'  Onglet Fichier_Train_Tmp : {len(df)} lignes')
    print(f'  Onglet Synthese_Gares    : {len(summary)} gares')

    # Stats par source
    print('\nRépartition par source :')
    for src, grp in df.groupby('Source_Donnee'):
        print(f'  {src:12s} {len(grp):6d} lignes')


if __name__ == '__main__':
    main()
