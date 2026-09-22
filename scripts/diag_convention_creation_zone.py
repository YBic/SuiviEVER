"""
diag_convention_creation_zone.py — suite
Verifie si Nombre_Interviews_A_Faire peut etre JSON null (cle presente, valeur
null) dans Prc_Vacation_Zone_Insert, puisque l'ecran de creation des specs
(§7.3.3) ne propose pas de champ objectif.

Simulation uniquement (@pSimulation=1), aucune ecriture.
"""
import json
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


def test_insert_simulation(cur, label, payload):
    print(f'\n-- {label} --')
    js = json.dumps(payload)
    print(f'   JSON envoye : {js}')
    try:
        cur.execute(
            "EXEC dbo.Prc_Vacation_Zone_Insert @pJSON=?, @pVacation_Rattrapage_Only=0, @pSimulation=1",
            (js,)
        )
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print('   OK — resultat :')
            print('   ' + ' | '.join(cols))
            for r in rows:
                print('   ' + ' | '.join('NULL' if v is None else str(v) for v in r))
        else:
            print('   OK — aucun jeu de resultat')
    except pyodbc.Error as e:
        print(f'   ERREUR SQL : {str(e)[:400]}')


def main():
    conn = connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT ID_Zone_Enquete FROM dbo.Zone_Enquete WHERE Code_Zone_Enquete = 'ANNEMASSE'")
    id_zone = cur.fetchone()[0]

    test_insert_simulation(cur, 'Nombre_Interviews_A_Faire = null (cle presente, valeur JSON null)', [{
        'ID_Societe_Terrain': 2,
        'Date_Vacation': '20270604',
        'ID_Zone_Enquete': id_zone,
        'Numero_Enqueteur_1': 1,
        'Numero_Enqueteur_2': None,
        'Nombre_Interviews_A_Faire': None,
        'ID_Vacation_Zone_A_Rattraper': None,
    }])

    conn.close()
    print('\nTermine (simulation uniquement, aucune ecriture).')


if __name__ == '__main__':
    main()
