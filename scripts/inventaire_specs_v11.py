"""
inventaire_specs_v11.py
LECTURE SEULE : inventaire de l'existant en base pour les specs v1.1
(EVER_2026_Site_Suivi_Affectation_20260730.docx).

Etape 2 : Philippe a deja modifie Prc_Vacation_Zone_Insert le 2026-08-18.
On regarde precisement ce qui est deja livre cote base, pour ne pas
re-specifier du travail deja fait.

Aucune ecriture.

Usage :
  python scripts/inventaire_specs_v11.py
"""
import pyodbc

SERVER = r'SRV-LANSQL-03\MSSQLIFOPGE'
DB = 'EVER_EXP'
DUMP_DIR = None  # defini dans main()

# Objets a inspecter en detail (signatures + definitions)
SP_CLES = [
    'Prc_Vacation_Zone_Insert',
    'Prc_Vacation_Zone_Affectation',
    'Prc_Vacation_Zone_Site_Insert',
    'Prc_Utilisateur_Insert',
]
TVF_CLES = [
    'ft_Vacation_Zone',
    'ft_Extranet_Vacation_Zone_Pivot',
]


def connect(db):
    erreurs = []
    for serveur in (SERVER, '10.10.1.27,2067'):
        try:
            conn = pyodbc.connect(
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={serveur};DATABASE={db};'
                f'Trusted_Connection=yes;TrustServerCertificate=yes;',
                timeout=15)
            print(f'   (connecte via {serveur})')
            return conn
        except Exception as e:
            erreurs.append(f'{serveur} -> {str(e)[:120]}')
    raise RuntimeError('Aucune connexion possible :\n     ' + '\n     '.join(erreurs))


def show(cur, title, sql, params=(), limit=80):
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
    from pathlib import Path
    dump_dir = Path(__file__).resolve().parent.parent / 'docs' / '_diag'
    dump_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(DB)
    cur = conn.cursor()
    print('=' * 78)
    print(f'INVENTAIRE SPECS v1.1 — etape 2 — base {DB}')
    print('=' * 78)

    # 1. Le vrai nom des tables "zone"
    show(cur, 'Tables dont le nom contient Zone ou Site',
         """SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME LIKE '%Zone%' OR TABLE_NAME LIKE '%Site%'
            ORDER BY TABLE_TYPE, TABLE_NAME""")

    # 2. Structure de Zone_Enquete (le referentiel des zones)
    show(cur, 'Colonnes de Zone_Enquete',
         """SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='Zone_Enquete' ORDER BY ORDINAL_POSITION""")

    show(cur, 'Contenu de Zone_Enquete (les zones disponibles)',
         'SELECT * FROM dbo.Zone_Enquete ORDER BY 1', limit=40)

    # 3. Ou est stocke l'enqueteur affecte a une vacation zone ?
    show(cur, 'Colonnes de Vacation_Zone_Site',
         """SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='Vacation_Zone_Site' ORDER BY ORDINAL_POSITION""")

    # 4. Signatures des SP / TVF cles
    for obj in SP_CLES + TVF_CLES:
        show(cur, f'Parametres de {obj}',
             """SELECT p.name AS Parametre, t.name AS Type, p.max_length,
                       p.is_output, p.has_default_value, p.default_value
                FROM sys.parameters p
                JOIN sys.types t ON t.user_type_id = p.user_type_id
                WHERE p.object_id = OBJECT_ID(?)
                ORDER BY p.parameter_id""", (f'dbo.{obj}',))

    # 5. Dump des definitions pour lecture detaillee
    print('\n-- Dump des definitions --')
    for obj in SP_CLES + TVF_CLES:
        try:
            cur.execute('SELECT OBJECT_DEFINITION(OBJECT_ID(?))', (f'dbo.{obj}',))
            row = cur.fetchone()
            if not row or not row[0]:
                print(f'   [!] indisponible : {obj}')
                continue
            out = dump_dir / f'{obj}.sql'
            out.write_text(row[0], encoding='utf-8')
            print(f'   {obj:<40} -> {row[0].count(chr(10)) + 1:>5} lignes')
        except Exception as e:
            print(f'   ERREUR {obj} : {str(e)[:200]}')

    # 6. Une colonne "Voxco" existe-t-elle quelque part ?
    show(cur, 'Colonnes contenant "Voxco" (case a cocher des specs 7.2)',
         """SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE COLUMN_NAME LIKE '%Voxco%' ORDER BY TABLE_NAME, COLUMN_NAME""")

    # 7. Etat des enqueteurs ST (ce que l'ecran 7.2 doit afficher)
    show(cur, 'Enqueteur_Terrain_Non_IFOP : repartition par societe et etat mission',
         """SELECT ID_Societe_Terrain,
                   COUNT(*) AS Nb,
                   SUM(CASE WHEN Date_Fin_Mission IS NULL THEN 1 ELSE 0 END) AS Nb_Actifs,
                   MIN(Matricule_Enqueteur_Terrain) AS Matricule_Min,
                   MAX(Matricule_Enqueteur_Terrain) AS Matricule_Max
            FROM dbo.Enqueteur_Terrain_Non_IFOP
            GROUP BY ID_Societe_Terrain ORDER BY 1""")

    # 8. Vacation_Zone : combien d'enqueteurs par vacation aujourd'hui ?
    show(cur, 'Vacation_Zone : nb de lignes par (date, zone, numero vacation)',
         """SELECT Nb_Lignes_Par_Vacation = Nb, COUNT(*) AS Occurrences
            FROM (SELECT COUNT(*) AS Nb
                  FROM dbo.Vacation_Zone
                  GROUP BY Date_Vacation, ID_Zone_Enquete, Numero_Vacation) t
            GROUP BY Nb ORDER BY 1""")

    show(cur, 'Vacation_Zone : valeurs de Rang_Enqueteur / Numero_Enqueteur',
         """SELECT Rang_Enqueteur, Numero_Enqueteur, COUNT(*) AS Nb
            FROM dbo.Vacation_Zone
            GROUP BY Rang_Enqueteur, Numero_Enqueteur
            ORDER BY 1,2""")

    conn.close()
    print('\nTermine.')


if __name__ == '__main__':
    main()
