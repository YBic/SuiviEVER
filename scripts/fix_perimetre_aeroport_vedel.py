"""
fix_perimetre_aeroport_vedel.py
Correctif : redonne a VEDEL_R (Robin, ID_Utilisateur=51) le perimetre d'aeroports
standard des comptes ADMIN_IFOP, afin qu'il revoie les vacations aeriennes.

Contexte (diagnostic du 2026-08-17, cf. scripts/diag_suivi_aeroport.py) :
  ft_EVER_Tableau_Aeroport_Chef_Equipe_Selection filtre les vacations visibles sur
  Aeroport_Depart_Utilisateur. Les 15 comptes ADMIN_IFOP ont tous le meme perimetre
  (ID_Aeroport 72,212,226,234,241,248,333) ; VEDEL_R n'en avait aucun, et n'en a
  jamais eu. Son role etait pourtant correct (ADMIN_IFOP), d'ou l'incoherence entre
  l'affichage "Administrateur IFOP" dans l'appli et le tableau vide.

Le perimetre est recopie depuis BICREL_Y (ID_Utilisateur=1), reference saine.
La clause NOT EXISTS rend le script rejouable sans creer de doublon (une cle unique
existe de toute facon sur (ID_Utilisateur, ID_Aeroport)).
Les colonnes d'audit sont laissees aux valeurs par defaut et aux triggers de la table.

Reversible :
  DELETE FROM dbo.Aeroport_Depart_Utilisateur WHERE ID_Utilisateur = 51;

Usage :
  python scripts/fix_perimetre_aeroport_vedel.py
"""
import pyodbc

SERVER = r'SRV-LANSQL-03\MSSQLIFOPGE'
DB = 'EVER_EXP'

ID_CIBLE = 51    # VEDEL_R
ID_MODELE = 1    # BICREL_Y
LOGIN_CIBLE = 'VEDEL_R'


def connect(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};DATABASE={db};'
        f'Trusted_Connection=yes;TrustServerCertificate=yes;',
        timeout=15)


def perimetre(cur, id_utilisateur):
    cur.execute(
        'SELECT ID_Aeroport FROM dbo.Aeroport_Depart_Utilisateur '
        'WHERE ID_Utilisateur = ? ORDER BY ID_Aeroport', (id_utilisateur,))
    return [r[0] for r in cur.fetchall()]


def nb_lignes_tvf(cur, login, date_vol):
    cur.execute(
        'SELECT COUNT(*) FROM dbo.ft_EVER_Tableau_Aeroport_Chef_Equipe('
        '?,NULL,?,NULL,NULL,NULL,NULL,NULL)', (login, date_vol))
    return cur.fetchone()[0]


def main():
    conn = connect(DB)
    cur = conn.cursor()
    print(f'Base : {DB}   Serveur : {SERVER}')
    print('=' * 70)

    # ── Etat avant ────────────────────────────────────────────────────────────
    avant = perimetre(cur, ID_CIBLE)
    modele = perimetre(cur, ID_MODELE)
    print(f'\nAVANT')
    print(f'  Perimetre modele (ID={ID_MODELE}) : {modele}')
    print(f'  Perimetre {LOGIN_CIBLE} (ID={ID_CIBLE}) : {avant}')
    print(f'  TVF {LOGIN_CIBLE} au 2026-08-17 : {nb_lignes_tvf(cur, LOGIN_CIBLE, "2026-08-17")} lignes')

    if not modele:
        print('\n[X] Le perimetre modele est vide : correctif abandonne.')
        conn.close()
        return

    # ── Correctif ─────────────────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO dbo.Aeroport_Depart_Utilisateur (ID_Utilisateur, ID_Aeroport)
        SELECT ?, adu.ID_Aeroport
        FROM dbo.Aeroport_Depart_Utilisateur adu
        WHERE adu.ID_Utilisateur = ?
          AND NOT EXISTS (
              SELECT 1 FROM dbo.Aeroport_Depart_Utilisateur x
              WHERE x.ID_Utilisateur = ? AND x.ID_Aeroport = adu.ID_Aeroport)
    """, (ID_CIBLE, ID_MODELE, ID_CIBLE))
    inserees = cur.rowcount
    conn.commit()
    print(f'\nINSERT : {inserees} ligne(s) inseree(s), transaction validee.')

    # ── Verification apres ────────────────────────────────────────────────────
    apres = perimetre(cur, ID_CIBLE)
    print(f'\nAPRES')
    print(f'  Perimetre {LOGIN_CIBLE} : {apres}')
    print(f'  Identique au modele : {apres == modele}')

    print(f'\n  Verification de la TVF pour {LOGIN_CIBLE} :')
    for d in ('2026-06-09', '2026-08-13', '2026-08-17', '2026-08-20'):
        print(f'    {d} : {nb_lignes_tvf(cur, LOGIN_CIBLE, d):>6} lignes')

    print('\n  Comparaison avec un compte sain (BICREL_Y) :')
    for d in ('2026-06-09', '2026-08-17'):
        print(f'    {d} : {nb_lignes_tvf(cur, "BICREL_Y", d):>6} lignes')

    # ── Plus aucun ADMIN_IFOP sans perimetre ? ────────────────────────────────
    cur.execute("""
        SELECT u.Utilisateur_Login
        FROM dbo.Utilisateur u
        LEFT JOIN dbo.Aeroport_Depart_Utilisateur adu ON adu.ID_Utilisateur = u.ID_Utilisateur
        OUTER APPLY (SELECT TOP 1 Code_Role
                     FROM dbo.ft_Utilisateur_Role_Effectif(NULL, u.Utilisateur_Login, NULL, NULL)) r
        WHERE adu.ID_Utilisateur IS NULL AND r.Code_Role = 'ADMIN_IFOP'
    """)
    restants = [r[0] for r in cur.fetchall()]
    print(f'\n  Comptes ADMIN_IFOP encore sans perimetre : {restants if restants else "aucun"}')

    conn.close()
    print('\nTermine.')


if __name__ == '__main__':
    main()
