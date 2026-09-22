"""
diag_suivi_aeroport.py
Diagnostic LECTURE SEULE de l'incident "Robin ne voit plus les vacations aeriennes".

CAUSE IDENTIFIEE (base EVER_EXP) :
  Les 15 comptes ADMIN_IFOP ont tous le meme perimetre de 7 aeroports dans
  Aeroport_Depart_Utilisateur : 72,212,226,234,241,248,333.
  VEDEL_R (ID_Utilisateur=51) est le seul a n'en avoir aucun, et n'en a jamais eu
  (0 ligne, aucune soft-suppression). Le filtre de visibilite de
  ft_EVER_Tableau_Aeroport_Chef_Equipe_Selection ne lui renvoie donc rien.

Cette etape : verifier la structure de la table avant d'ecrire le correctif
(colonne identity ? contraintes ? valeurs par defaut ?).

Aucune ecriture.

Usage :
  python scripts/diag_suivi_aeroport.py
"""
import pyodbc

SERVER = r'SRV-LANSQL-03\MSSQLIFOPGE'
DB = 'EVER_EXP'
TABLE = 'Aeroport_Depart_Utilisateur'


def connect(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};DATABASE={db};'
        f'Trusted_Connection=yes;TrustServerCertificate=yes;',
        timeout=15)


def show(cur, title, sql, params=(), limit=60):
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
        return rows
    except Exception as e:
        print(f'   ERREUR : {str(e)[:300]}')
        return []


def main():
    conn = connect(DB)
    cur = conn.cursor()
    print('=' * 78)
    print(f'BASE : {DB}   TABLE : {TABLE}')
    print('=' * 78)

    show(cur, 'Colonnes : nullabilite, identity, valeur par defaut',
         """SELECT c.name AS Colonne, t.name AS Type, c.is_nullable AS Nullable,
                   c.is_identity AS Identity_, OBJECT_DEFINITION(c.default_object_id) AS Defaut
            FROM sys.columns c
            JOIN sys.types t ON t.user_type_id = c.user_type_id
            WHERE c.object_id = OBJECT_ID(?)
            ORDER BY c.column_id""", (f'dbo.{TABLE}',))

    show(cur, 'Contraintes et index',
         """SELECT i.name AS Index_, i.type_desc, i.is_unique, i.is_primary_key,
                   STRING_AGG(c.name, ',') WITHIN GROUP (ORDER BY ic.key_ordinal) AS Colonnes
            FROM sys.indexes i
            JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            JOIN sys.columns c ON c.object_id=i.object_id AND c.column_id=ic.column_id
            WHERE i.object_id = OBJECT_ID(?)
            GROUP BY i.name, i.type_desc, i.is_unique, i.is_primary_key""", (f'dbo.{TABLE}',))

    show(cur, 'Triggers sur la table',
         """SELECT name, is_disabled FROM sys.triggers WHERE parent_id = OBJECT_ID(?)""",
         (f'dbo.{TABLE}',))

    conn.close()
    print('\nTermine.')


if __name__ == '__main__':
    main()
