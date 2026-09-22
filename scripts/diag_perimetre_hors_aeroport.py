"""
diag_perimetre_hors_aeroport.py
Verification LECTURE SEULE : le trou d'habilitation corrige pour VEDEL_R cote aeroport
existe-t-il aussi cote hors-aeroport (zones) ?

Cote aeroport, la visibilite passait par Aeroport_Depart_Utilisateur. On cherche
l'equivalent pour ft_EVER_Tableau_Zone_Chef_Equipe et on compare VEDEL_R a BICREL_Y.

Aucune ecriture.

Usage :
  python scripts/diag_perimetre_hors_aeroport.py
"""
import pyodbc

SERVER = r'SRV-LANSQL-03\MSSQLIFOPGE'
DB = 'EVER_EXP'
LOGIN_KO = 'VEDEL_R'
LOGIN_OK = 'BICREL_Y'


def connect(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};DATABASE={db};'
        f'Trusted_Connection=yes;TrustServerCertificate=yes;',
        timeout=15)


def show(cur, title, sql, params=(), limit=40):
    print(f'\n-- {title} --')
    try:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        if not rows:
            print('   (aucun resultat)')
            return []
        print('   ' + ' | '.join(cols))
        for r in rows[:limit]:
            print('   ' + ' | '.join('NULL' if v is None else str(v) for v in r))
        if len(rows) > limit:
            print(f'   ... ({len(rows)} lignes)')
        return rows
    except Exception as e:
        print(f'   ERREUR : {str(e)[:300]}')
        return []


def main():
    conn = connect(DB)
    cur = conn.cursor()
    print(f'Base : {DB}   |  KO={LOGIN_KO}  OK={LOGIN_OK}')
    print('=' * 70)

    # 1. Volumetrie des vacations zone, pour choisir une date pertinente
    show(cur, 'Vacation_Zone par mois',
         """SELECT FORMAT(Date_Vacation,'yyyy-MM') AS Mois, COUNT(*) AS Nb
            FROM dbo.Vacation_Zone GROUP BY FORMAT(Date_Vacation,'yyyy-MM') ORDER BY 1""")

    # 2. La TVF hors-aeroport, pour les deux comptes
    #    Signature (cf. core/db.py) : (login, societe, date, ?, NULL, ?, ?)
    print('\n-- ft_EVER_Tableau_Zone_Chef_Equipe : VEDEL_R vs BICREL_Y --')
    for d in ('2026-06-09', '2026-08-13', '2026-08-17'):
        ligne = f'   {d} : '
        for login in (LOGIN_KO, LOGIN_OK):
            try:
                cur.execute(
                    'SELECT COUNT(*) FROM dbo.ft_EVER_Tableau_Zone_Chef_Equipe('
                    '?,NULL,?,NULL,NULL,NULL,NULL)', (login, d))
                ligne += f'{login}={cur.fetchone()[0]:<8}'
            except Exception as e:
                ligne += f'{login}=ERR({str(e)[:70]}) '
        print(ligne)

    # 3. Existe-t-il une table de perimetre cote zone ?
    show(cur, 'Tables de perimetre potentielles (Zone / Site / Region liees a Utilisateur)',
         """SELECT DISTINCT c.TABLE_NAME, c.COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.COLUMN_NAME IN ('ID_Utilisateur','Utilisateur_Login')
              AND (c.TABLE_NAME LIKE '%Zone%' OR c.TABLE_NAME LIKE '%Site%'
                   OR c.TABLE_NAME LIKE '%Region%' OR c.TABLE_NAME LIKE '%Departement%')
            ORDER BY c.TABLE_NAME""")

    conn.close()
    print('\nTermine.')


if __name__ == '__main__':
    main()
