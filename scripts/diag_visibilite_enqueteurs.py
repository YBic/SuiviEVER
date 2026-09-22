"""
diag_visibilite_enqueteurs.py
LECTURE SEULE — point de controle souleve par l'inventaire specs v1.1 :

Les comptes de connexion au format A#### (matricules des 65 enqueteurs Solutions
Terrain) renvoyaient 256 lignes au 2026-08-17 dans ft_EVER_Tableau_Aeroport_Chef_Equipe,
soit AUTANT que les comptes administrateurs. Or les specs (§4.8) prevoient que le
profil Enqueteur ne voit que « Vacations affectees ».

On verifie quel role porte reellement ces comptes et ce qu'ils voient.

Aucune ecriture.

Usage :
  python scripts/diag_visibilite_enqueteurs.py
"""
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
        print(f'   ERREUR : {str(e)[:250]}')
        return []


def main():
    conn = connect(DB)
    cur = conn.cursor()
    print('=' * 78)
    print(f'VISIBILITE DES COMPTES ENQUETEURS — base {DB}')
    print('=' * 78)

    # 1. Quel role portent les comptes A#### ?
    show(cur, 'Roles des comptes de connexion, par format de login',
         """SELECT r.Code_Role,
                   CASE WHEN u.Utilisateur_Login LIKE 'A[0-9][0-9][0-9][0-9]' THEN 'A#### (matricule ST)'
                        WHEN u.Utilisateur_Login LIKE '[0-9]%'                THEN 'numerique (IFOP ?)'
                        ELSE 'alphabetique (nomme)' END AS Format_Login,
                   COUNT(*) AS Nb
            FROM dbo.Utilisateur u
            OUTER APPLY (SELECT TOP 1 Code_Role
                         FROM dbo.ft_Utilisateur_Role_Effectif(NULL, u.Utilisateur_Login, NULL, NULL)) r
            GROUP BY r.Code_Role,
                     CASE WHEN u.Utilisateur_Login LIKE 'A[0-9][0-9][0-9][0-9]' THEN 'A#### (matricule ST)'
                          WHEN u.Utilisateur_Login LIKE '[0-9]%'                THEN 'numerique (IFOP ?)'
                          ELSE 'alphabetique (nomme)' END
            ORDER BY 1, 2""")

    # 2. Perimetre aeroport de ces comptes
    show(cur, 'Perimetre Aeroport_Depart_Utilisateur par role',
         """SELECT r.Code_Role, COUNT(DISTINCT u.ID_Utilisateur) AS Nb_Comptes,
                   SUM(CASE WHEN adu.ID_Utilisateur IS NULL THEN 0 ELSE 1 END) AS Nb_Lignes_Perimetre
            FROM dbo.Utilisateur u
            OUTER APPLY (SELECT TOP 1 Code_Role
                         FROM dbo.ft_Utilisateur_Role_Effectif(NULL, u.Utilisateur_Login, NULL, NULL)) r
            LEFT JOIN dbo.Aeroport_Depart_Utilisateur adu ON adu.ID_Utilisateur = u.ID_Utilisateur
            GROUP BY r.Code_Role ORDER BY 1""")

    # 3. Ce que voit un echantillon de comptes A#### au 2026-08-17
    show(cur, 'Lignes vues au 2026-08-17 par role (echantillon de 3 comptes par role)',
         """WITH C AS (
                SELECT u.Utilisateur_Login, r.Code_Role,
                       ROW_NUMBER() OVER (PARTITION BY r.Code_Role ORDER BY u.Utilisateur_Login) AS rn
                FROM dbo.Utilisateur u
                OUTER APPLY (SELECT TOP 1 Code_Role
                             FROM dbo.ft_Utilisateur_Role_Effectif(NULL, u.Utilisateur_Login, NULL, NULL)) r
            )
            SELECT C.Code_Role, C.Utilisateur_Login, x.Nb_Lignes
            FROM C
            CROSS APPLY (SELECT COUNT(*) AS Nb_Lignes
                         FROM dbo.ft_EVER_Tableau_Aeroport_Chef_Equipe(
                              C.Utilisateur_Login,NULL,'2026-08-17',NULL,NULL,NULL,NULL,NULL)) x
            WHERE C.rn <= 3
            ORDER BY C.Code_Role, C.Utilisateur_Login""", limit=60)

    conn.close()
    print('\nTermine.')


if __name__ == '__main__':
    main()
