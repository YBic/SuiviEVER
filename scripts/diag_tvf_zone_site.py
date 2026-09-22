"""LECTURE SEULE : colonnes retournees par ft_EVER_Tableau_Zone_Site_Chef_Equipe,
pour reperer comment identifier une gare ferroviaire (regle §6.4.2)."""
import pyodbc

SERVER = r'SRV-LANSQL-03\MSSQLIFOPGE'
DB = 'EVER_EXP'


def connect(db):
    for serveur in (SERVER, '10.10.1.27,2067'):
        try:
            return pyodbc.connect(
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={serveur};DATABASE={db};'
                f'Trusted_Connection=yes;TrustServerCertificate=yes;', timeout=15)
        except Exception:
            continue
    raise RuntimeError('connexion impossible')


conn = connect(DB)
cur = conn.cursor()

cur.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.ft_EVER_Tableau_Zone_Site_Chef_Equipe'))")
definition = cur.fetchone()[0]
from pathlib import Path
out = Path(__file__).resolve().parent.parent / 'docs' / '_diag' / 'ft_EVER_Tableau_Zone_Site_Chef_Equipe.sql'
out.write_text(definition, encoding='utf-8')
print(f'Definition ecrite : {out} ({definition.count(chr(10))+1} lignes)')

# Trouver une vacation zone avec au moins un site gare de train, pour tester en direct
cur.execute("""
    SELECT TOP 1 vz.ID_Vacation_Zone
    FROM dbo.Vacation_Zone_Site vzs
    JOIN dbo.Type_Site ts ON ts.ID_Type_Site = vzs.ID_Type_Site
    JOIN dbo.Vacation_Zone vz ON vz.ID_Vacation_Zone = vzs.ID_Vacation_Zone
    WHERE ts.Code_Type_Site = 'GARE_TRAIN'
""")
row = cur.fetchone()
id_vac = row[0] if row else None
print(f'\nID_Vacation_Zone de test (contient une gare train) : {id_vac}')

if id_vac:
    cur.execute("SELECT * FROM dbo.ft_EVER_Tableau_Zone_Site_Chef_Equipe(NULL, ?, NULL)", (id_vac,))
    cols = [d[0] for d in cur.description]
    print('\nColonnes : ' + ' | '.join(cols))
    for r in cur.fetchall():
        print(' | '.join('NULL' if v is None else str(v) for v in r))

conn.close()
