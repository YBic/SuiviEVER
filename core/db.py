"""
Couche d'accès aux données SQL Server – EVER 2026.

Signatures vérifiées directement sur EVER_DEV le 28/04/2026.

Rappel : TVF → SELECT * FROM dbo.fn(...)   |   SP → EXEC dbo.Prc_...  + commit()
"""
import logging
import re

import pyodbc

from accounts.db import get_connection

logger = logging.getLogger('ever.db')

# Capture le texte du message ET son numero d'erreur SQL Server.
# Seuls les numeros >= 50000 sont des messages applicatifs (RAISERROR / THROW) :
# en dessous, c'est une erreur systeme, dont le texte peut exposer des noms
# d'objets de la base. Voir _extract_sql_message.
_SQL_MSG_RE = re.compile(r'\[SQL Server\](.+?)\s*\((\d+)\)\s*\(SQL\w+\)\s*$')
_SQL_USER_ERROR_MIN = 50000


def _extract_sql_message(exc: pyodbc.Error) -> str:
    """
    Extrait le message RAISERROR (déjà en français, écrit pour l'utilisateur final)
    du bruit ajouté par le driver ODBC. Ex :
      "[42000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Le numéro de
       l'enquêteur 1 doit être renseigné et supérieur à 0. (50000) (SQLMoreResults)"
      -> "Le numéro de l'enquêteur 1 doit être renseigné et supérieur à 0."
    Tout ce qui n'est pas un message applicatif (numéro d'erreur < 50000, ou
    format inattendu) est remplacé par un message générique : le texte des
    erreurs système de SQL Server expose des noms d'objets de la base
    (contraintes, tables), ce qui relève de la fuite d'informations techniques
    relevée par l'audit 2026. L'exception complète reste journalisée.
    """
    raw = str(exc.args[1]) if len(exc.args) > 1 else str(exc)
    m = _SQL_MSG_RE.search(raw)
    if m and int(m.group(2)) >= _SQL_USER_ERROR_MIN:
        return m.group(1).strip()
    logger.error('Erreur SQL sans message métier exploitable : %s', raw)
    return "Une erreur technique est survenue lors de l'enregistrement."


def _message_json_output(resultat: dict) -> str:
    """
    Message d'erreur affichable à partir du @pJsonOutput d'une procédure
    ([{"ErrorNumber":n,"ErrorMessage":"..."}]).

    Même règle que _extract_sql_message : seuls les numéros >= 50000 sont des
    messages applicatifs écrits pour l'utilisateur. En dessous, c'est une erreur
    système dont le texte expose des noms de base, de table ou de contrainte —
    la fuite d'informations techniques relevée par l'audit 2026. On journalise
    le détail et on renvoie un message générique.
    """
    numero  = resultat.get('ErrorNumber') or 0
    message = (resultat.get('ErrorMessage') or '').strip()
    if numero >= _SQL_USER_ERROR_MIN and message:
        return message
    logger.error('Erreur SQL %s remontée par une procédure : %s', numero, message)
    return "Une erreur technique est survenue lors de l'enregistrement."


def _rows_to_dicts(cursor) -> list[dict]:
    """Convertit les lignes d'un curseur pyodbc en liste de dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Listes de référence (filtres / menus déroulants)
# ---------------------------------------------------------------------------

def get_periodes() -> list[dict]:
    """
    ft_EVER_Liste_Periode_Terrain(@pID_Periode_Terrain, @pDate_Debut, @pDate_Fin, @pID_Vague)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dbo.ft_EVER_Liste_Periode_Terrain(NULL,NULL,NULL,NULL)")
        return _rows_to_dicts(cursor)


def get_dates_vols(
    id_societe_terrain: int | None = None,
    matricule:          str | None = None,
    date_debut:         str | None = None,
    date_fin:           str | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Dates_des_Vols(
        @pID_Societe_Terrain  tinyint  NULL ok
        @pMatricule           varchar  NULL ok
        @pDate_Vol_Debut      date     NULL ok
        @pDate_Vol_Fin        date     NULL ok
    )
    Retourne : [{'Date du Vol': date}, ...]
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Dates_des_Vols(?,?,?,?)",
            (id_societe_terrain, matricule, date_debut, date_fin)
        )
        return _rows_to_dicts(cursor)


def get_aeroports(
    date_vacation:      str,
    user_login:         str,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Aeroports_Vacation(
        @pUtilisateur_Login   varchar  NULL ok
        @pID_Societe_Terrain  tinyint  NULL ok
        @pDate_Debut          date     NULL ok
        @pDate_Fin            date     NULL ok
    )
    Retourne une ligne par (enquêteur, aéroport).
    La vue déduplique sur ID_Aeroport pour le dropdown.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Aeroports_Vacation(?,?,?,?)",
            (user_login, id_societe_terrain, date_vacation, date_vacation)
        )
        rows = _rows_to_dicts(cursor)

    # Dédoublonnage par ID_Aeroport pour le dropdown
    seen = set()
    aeroports = []
    for r in rows:
        if r['ID_Aeroport'] not in seen:
            seen.add(r['ID_Aeroport'])
            aeroports.append({
                'Id_Aeroport':   r['ID_Aeroport'],
                'Code_Aeroport': r['Code_Aeroport'],
                'Nom_Aeroport':  r['Nom_Aeroport'],
            })
    return aeroports


def get_types_vol(
    date_vacation:      str,
    id_aeroport:        int | None = None,
    id_societe_terrain: int | None = None,
    id_type_vacation_vol: int | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Type_Vacation_Vol_Date_Aeroport(
        @pID_Societe_Terrain    tinyint  NULL ok
        @pDate_Vol              date     NULL ok
        @pID_Aeroport           smallint NULL ok
        @pID_Type_Vacation_Vol  tinyint  NULL ok
    )
    Retourne : ID_Type_Vacation_Vol, Code_Type_Vacation_Vol, Type_Vacation_Vol, Ordre_Affichage
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Type_Vacation_Vol_Date_Aeroport(?,?,?,?)",
            (id_societe_terrain, date_vacation, id_aeroport, id_type_vacation_vol)
        )
        return _rows_to_dicts(cursor)


def get_numeros_vol(
    date_vacation:        str,
    id_aeroport:          int | None = None,
    id_personne:          int | None = None,
    id_type_vacation_vol: int | None = None,
    id_societe_terrain:   int | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Numero_Vol_Date_Aeroport(
        @pID_Societe_Terrain    tinyint  NULL ok
        @pDate_Vol              date     NULL ok
        @pID_Aeroport           smallint NULL ok
        @pID_Personne           int      NULL ok
        @pID_Type_Vacation_Vol  tinyint  NULL ok
    )
    Retourne : ID_ENPA_Vol_Split, Numero_Vol
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Numero_Vol_Date_Aeroport(?,?,?,?,?)",
            (id_societe_terrain, date_vacation, id_aeroport, id_personne, id_type_vacation_vol)
        )
        return _rows_to_dicts(cursor)


def get_enqueteurs_aeroport(
    date_vacation:      str,
    id_aeroport:        int | None = None,
    id_societe_terrain: int | None = None,
    id_type_vol:        int | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteur_Date_Aeroport(
        @pID_Societe_Terrain    tinyint  NULL ok
        @pDate_Debut            date     NULL ok
        @pDate_Fin              date     NULL ok
        @pID_Aeroport           smallint NULL ok
        @pID_Type_Vacation_Vol  tinyint  NULL ok
    )
    Retourne : Matricule, ID_Personne, Nom, Prenom, Libelle_Enqueteur
    → normalisé : ID_Personne → Id_Personne (cohérence avec le JS)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Date_Aeroport(?,?,?,?,?)",
            (id_societe_terrain, date_vacation, date_vacation, id_aeroport, id_type_vol)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        result.append({
            'Id_Personne':       r.get('ID_Personne'),
            'Libelle_Enqueteur': r.get('Libelle_Enqueteur') or '',
        })
    return result


def get_sites(
    date_vacation:      str,
    id_societe_terrain: int | None = None,
    id_personne:        int | None = None,
) -> list[dict]:
    """
    ft_Extranet_Vacation_Zone — zones distinctes pour le dropdown filtre.
    Paramètres utilisés : ID_Societe_Terrain, Date_Debut/Fin, ID_Enqueteur.
    Retourne : Id_Site, Nom_Site, Type_Site.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Zone(?,NULL,NULL,NULL,NULL,?,?,NULL,NULL,?)",
            (id_societe_terrain, date_vacation, date_vacation, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

    seen = set()
    sites = []
    for r in raw_rows:
        key = r.get('ID_Zone_Enquete')
        if key not in seen:
            seen.add(key)
            sites.append({
                'Id_Site':  key,
                'Nom_Site': r.get('Zone_Enquete') or '',
                'Type_Site': 'ZONE',
            })
    return sites


def get_enqueteurs_site(
    date_vacation:      str,
    id_site:            int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_Extranet_Vacation_Zone — enquêteurs distincts pour le dropdown filtre,
    filtrés par zone (@pID_Zone_Enquete) et date.
    Retourne : Id_Personne, Libelle_Enqueteur.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Zone(?,NULL,?,NULL,NULL,?,?,NULL,NULL,NULL)",
            (id_societe_terrain, id_site, date_vacation, date_vacation)
        )
        raw_rows = _rows_to_dicts(cursor)

    seen = set()
    enqueteurs = []
    for r in raw_rows:
        id_enq = r.get('ID_Enqueteur')
        if id_enq and id_enq not in seen:
            seen.add(id_enq)
            enqueteurs.append({
                'Id_Personne':       id_enq,
                'Libelle_Enqueteur': r.get('Enqueteur') or '',
            })
    return enqueteurs


# ---------------------------------------------------------------------------
# Tableau de suivi aéroport  (écran principal)
# ---------------------------------------------------------------------------

def get_suivi_aeroport(
    date_vacation:      str,
    user_login:         str,
    id_societe_terrain: int | None = None,
    id_aeroport:        int | None = None,
    id_type_vol:        int | None = None,
    id_personne:        int | None = None,
) -> list[dict]:
    """
    ft_EVER_Tableau_Aeroport_Chef_Equipe(
        @pUtilisateur_Login     varchar  NULL ok   ← login session (pas matricule)
        @pID_Societe_Terrain    tinyint  NULL ok
        @pDate_Vol              date
        @pID_Aeroport           smallint NULL ok
        @pID_Type_Vacation_Vol  tinyint  NULL ok
        @pID_ENPA_VolSplit      int      NULL ok   ← toujours NULL côté web
        @pID_Personne           int      NULL ok
        @pDuree_Minute_Cloture  int      default=2 ← toujours NULL côté web
    )

    Notes :
    - La TVF retourne un résultat "enrichi" : lignes vacation + lignes total vol
      + lignes total aéroport. On filtre sur ID_Vacation_Vol IS NOT NULL pour
      ne garder que les lignes vacation (le JS calcule ses propres totaux).
    - Les noms de colonnes sont en français avec espaces/accents ; on les normalise
      ici pour que le JS reste indépendant de l'implémentation SQL.
    - Code IATA extrait du numéro de vol (ex: "U2" de "U2-4427").
    - Vols_Autres=1 : pas d'objectif, pas de taux, pas de commentaire vacation.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Aeroport_Chef_Equipe(?,?,?,?,?,NULL,?,NULL)",
            (user_login, id_societe_terrain, date_vacation, id_aeroport, id_type_vol, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

        # Garder uniquement les lignes vacation (pas les sous-totaux de la TVF)
        vacation_rows = [r for r in raw_rows if r.get('ID_Vacation_Vol') is not None]
        if not vacation_rows:
            return []

        # Noms d'aéroports (une seule requête pour tous les ID distincts)
        aero_ids = list({r['ID_Aeroport'] for r in vacation_rows if r.get('ID_Aeroport')})
        aero_names: dict[int, str] = {}
        if aero_ids:
            placeholders = ','.join('?' for _ in aero_ids)
            cursor.execute(
                f"SELECT ID_Aeroport, Nom_Aeroport FROM dbo.Aeroport WHERE ID_Aeroport IN ({placeholders})",
                aero_ids,
            )
            aero_names = {row[0]: row[1] for row in cursor.fetchall()}

        # Normalisation des colonnes
        result = []
        for r in vacation_rows:
            code_aero  = r.get('Code Aéroport Départ') or ''
            id_aero    = r.get('ID_Aeroport')
            num_vol    = r.get('N° Vol') or ''
            code_iata  = num_vol.split('-')[0] if '-' in num_vol else ''
            vols_autres = bool(r.get('Vols_Autres'))
            result.append({
                'ID_Vacation_Vol':        r.get('ID_Vacation_Vol'),
                'ID_Vacation_Enqueteur':  r.get('ID_Vacation_Enqueteur'),
                'ID_Personne':            r.get('ID_Personne'),
                'Rang_Enqueteur':         r.get('Rang_Enqueteur'),
                'Code_Aeroport':          code_aero,
                'Nom_Aeroport':           aero_names.get(id_aero, code_aero),
                'Numero_Vacation':        r.get('N° Vacation'),
                'Numero_Vol':             num_vol,
                'Code_Compagnie':         code_iata,
                'Nom_Compagnie':          r.get('Compagnie') or '',
                'Libelle_Enqueteur':      r.get('Enquêteur') or '',
                'Aeroport_Destination':   r.get('Destination') or '',
                'Heure_Depart':           r.get('Heure départ (Théorique)') or '',
                'ID_Type_Vacation_Vol':   r.get('ID_Type_Vacation_Vol'),
                'Type_Vacation_Vol':      r.get('Type_Vacation_Vol') or '',
                'Vols_Autres':            vols_autres,
                'Objectif':               r.get('Objectif Questionnaires') if not vols_autres else None,
                'Completes_100':          r.get('100% Completés') or 0,
                'Recrutes':               r.get('Recrutés') or 0,
                'Face_A_Face':            r.get('Completés Questions FAF') or 0,
                'Abandons':               r.get('Abandon') or 0,
                'Statut_Vol':             r.get('STATUT VOL') or '',
                'Commentaire_Vacation':   None if vols_autres else r.get('Commentaires_Vacation'),
                'Commentaire_Vol':        r.get('Commentaires_Vacation_Vol'),
            })
        return result


def get_id_personne_by_matricule(matricule: str, id_societe_terrain: int | None = None) -> int | None:
    """
    Résout l'ID_Personne d'un enquêteur à partir de son matricule (= login de connexion).

    Il n'existe pas de table maître "Personne" exposée à l'application : le lien
    Matricule → ID_Personne se trouve uniquement dans les données de vacation
    (Vacation_Vol côté aéroport, Vacation_Zone_Site côté zones). On lit donc l'une
    puis l'autre. Renvoie None si l'enquêteur n'a aucune vacation rattachée.

    Utilisé pour forcer @pID_Personne dans les TVFs de suivi quand le rôle est
    ENQUETEUR (un enquêteur ne doit voir que ses propres vacations).
    """
    if not matricule:
        return None
    with get_connection() as conn:
        cursor = conn.cursor()
        for table in ('Vacation_Vol', 'Vacation_Zone_Site'):
            cursor.execute(
                f"SELECT TOP 1 ID_Personne FROM dbo.{table} "
                f"WHERE Matricule_Enqueteur = ? AND ID_Personne IS NOT NULL",
                (matricule,)
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
    return None


def get_types_vol() -> list[dict]:
    """
    ft_EVER_Liste_Type_Vacation_Vol(@pID_Type_Vacation_Vol = NULL)
    Retourne les 4 types : Principal(1), Complémentaire(2), Optionnel(3), Autres(0).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dbo.ft_EVER_Liste_Type_Vacation_Vol(NULL)")
        rows = _rows_to_dicts(cursor)
    return [
        {
            'id':    r['ID_Type_Vacation_Vol'],
            'code':  r['Code_Type_Vacation_Vol'],
            'label': r['Type_Vacation_Vol'],
            'ordre': r['Ordre_Affichage'],
        }
        for r in sorted(rows, key=lambda x: x['Ordre_Affichage'])
    ]


# ---------------------------------------------------------------------------
# Tableau de suivi hors aéroport
# ---------------------------------------------------------------------------

def get_suivi_hors_aeroport(
    date_vacation:      str,
    user_login:         str | None = None,
    id_site:            int | None = None,
    id_personne:        int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_EVER_Tableau_Zone_Chef_Equipe(
        @pUtilisateur_Login   varchar
        @pID_Societe_Terrain  tinyint  NULL ok
        @pDate_Vacation_Min   date
        @pDate_Vacation_Max   date
        @pID_Vacation_Zone    int      NULL ok
        @pID_Zone_Enquete     smallint NULL ok   ← id_site
        @pID_Enqueteur        int      NULL ok   ← id_personne
    )

    Une ligne par vacation zone (bug multi-lignes corrigé côté SQL le 08/06).
    Les commentaires se gèrent depuis le détail des sites, pas ici.
    Le taux est recalculé côté JS.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Zone_Chef_Equipe(?,?,?,?,NULL,?,?)",
            (user_login, id_societe_terrain, date_vacation, date_vacation, id_site, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        if r.get('ID_Enqueteur') is None:      # ligne TOTAL éventuelle → ignorée
            continue
        date_v = r.get('Date_Vacation')
        result.append({
            'Id_Zone':           r.get('ID_Zone_Enquete'),
            'Nom_Zone':          r.get('Zone_Enquete') or '',
            'ID_Vacation':       r.get('ID_Vacation_Zone'),
            'Numero_Vacation':   r.get('Numero_Vacation'),
            'Rang_Enqueteur':    r.get('Rang_Enqueteur'),
            'Libelle_Enqueteur': r.get('Enqueteur') or '',
            'Date_Vacation':     str(date_v) if date_v else '',
            'Objectif':          r.get('Objectif'),   # peut être None
            'Completes_100':     int(r.get('Complete') or 0),
            'Recrutes':          int(r.get('Recrute') or 0),
            'Face_A_Face':       int(r.get('Complete_FAF') or 0),
            'Abandons':          int(r.get('Abandon') or 0),
            'A_Recruter':        r.get('A_Recruter'),
            'Refus':             int(r.get('Refus') or 0),
        })
    return result


def get_detail_vacation_hors_aeroport(id_vacation: int, user_login: str | None = None) -> list[dict]:
    """
    ft_EVER_Tableau_Zone_Site_Chef_Equipe(
        @pUtilisateur_Login varchar
        @pID_Vacation_Zone  int        ← id_vacation
        @pID_Enqueteur      int  NULL ok
    )
    Détail des sites d'une vacation zone : une ligne par site.
    Inclut les infos train et le commentaire au niveau site.
    """
    import datetime

    def _time_str(v):
        if v is None:
            return ''
        if isinstance(v, datetime.timedelta):
            total = int(v.total_seconds())
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
        if isinstance(v, datetime.time):
            return v.strftime('%H:%M')
        return str(v)[:5]

    with get_connection() as conn:
        cursor = conn.cursor()
        # ID_Type_Site de la gare ferroviaire, pour la règle §6.4.2 : ne pas
        # afficher les trains éligibles dans le détail d'une vacation.
        cursor.execute(
            "SELECT ID_Type_Site FROM dbo.Type_Site WHERE Code_Type_Site = 'GARE_TRAIN'"
        )
        row = cursor.fetchone()
        id_type_site_gare_train = row[0] if row else None

        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Zone_Site_Chef_Equipe(?,?,NULL)",
            (user_login, id_vacation)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        if r.get('ID_Enqueteur') is None:      # ligne TOTAL éventuelle → ignorée
            continue
        date_v = r.get('Date_Vacation')
        # §6.4.2 règle 04 : pour un site Gare Ferroviaire, ne pas afficher les
        # trains éligibles — même si la TVF les renvoie.
        is_gare_train = (
            id_type_site_gare_train is not None
            and r.get('ID_Type_Site') == id_type_site_gare_train
        )
        result.append({
            'ID_Vacation_Zone_Site':    r.get('ID_Vacation_Zone_Site'),
            'ID_Vacation_Zone':         r.get('ID_Vacation_Zone'),
            'ID_Site':                  r.get('ID_Site'),
            'Sites_Autres':             bool(r.get('Sites_Autres')),
            'Type_Site':                r.get('Type_Site') or '',
            'Code_Type_Site':           r.get('Type_Site') or '',
            'Nom_Site':                 r.get('Nom_Site') or '',
            'Date_Vacation':            str(date_v) if date_v else '',
            'Numero_Vacation':          r.get('Numero_Vacation'),
            'Rang_Enqueteur':           r.get('Rang_Enqueteur'),
            'ID_Enqueteur':             r.get('ID_Enqueteur'),
            'Libelle_Enqueteur':        r.get('Enqueteur') or '',
            'Matricule_Enqueteur':      r.get('Matricule_Enqueteur') or '',
            'Objectif_Total':           r.get('Objectif'),   # peut être None
            'Recrutes':                 int(r.get('Recrute') or 0),
            'Valides':                  int(r.get('Complete') or 0),
            'FAF_Valides':              int(r.get('Complete_FAF') or 0),
            'Abandons':                 int(r.get('Abandon') or 0),
            'A_Recruter':               r.get('A_Recruter'),
            'Refus':                    int(r.get('Refus') or 0),
            # Spécifique trains — masqué pour les gares ferroviaires (§6.4.2)
            'Nbre_Trains':              None if is_gare_train else r.get('Trajet_Train_Nbre_Trains'),
            'Gares_Terminus':           '' if is_gare_train else (r.get('Liste_Gare_Terminus_Train') or ''),
            'Pays_Terminus':            '' if is_gare_train else (r.get('Liste_Pays_Terminus_Train') or ''),
            'Heure_Train_Min':          '' if is_gare_train else _time_str(r.get('Trajet_Gare_Train_Heure_Depart_Min')),
            'Heure_Train_Max':          '' if is_gare_train else _time_str(r.get('Trajet_Gare_Train_Heure_Depart_Max')),
            # Commentaires
            'Commentaire_Vacation':     r.get('Commentaires_Vacation'),
            'Commentaire_Site':         r.get('Commentaires_Vacation_Site'),
        })
    return result


# ---------------------------------------------------------------------------
# Affectation
# ---------------------------------------------------------------------------

def get_aeroports_affectation(
    date_vacation:      str,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """ft_EVER_Liste_Aeroports_Affectation — TODO: signature à confirmer."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Aeroports_Affectation(?,?,?)",
            (id_societe_terrain, date_vacation, date_vacation)
        )
        return _rows_to_dicts(cursor)


def get_vacations_affectation(
    date_vacation:      str,
    id_aeroport:        int | None = None,
    id_personne:        int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_Extranet_Vacation_Aeroport_Pivot(
        @pID_Societe_Terrain    tinyint  NULL ok
        @pID_Aeroport           smallint NULL ok
        @pDate_Vacation_Debut   date
        @pDate_Vacation_Fin     date
        @pNumero_Vacation       varchar  NULL
        @pID_Personne           int      NULL ok
    )
    Colonnes normalisées :
      ID_Vacation_Enqueteur_1 → ID_Vacation (slot 1)
      ID_Vacation_Enqueteur_2 → ID_Vacation_2 (slot 2)
      Enqueteur_1/2           → Libelle_Enqueteur_1/2 (labels)
      Affectation_Modifiable  → bool
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Aeroport_Pivot(?,?,?,?,NULL,?)",
            (id_societe_terrain, id_aeroport, date_vacation, date_vacation, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

    def _time_str(v):
        """datetime.time ou timedelta → 'HH:MM', None → ''."""
        if v is None:
            return ''
        import datetime
        if isinstance(v, datetime.timedelta):
            total = int(v.total_seconds())
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
        return str(v)[:5]   # 'HH:MM:SS' → 'HH:MM'

    result = []
    for r in raw_rows:
        date_v = r.get('Date_Vacation')
        result.append({
            'ID_Vacation':             r.get('ID_Vacation_Enqueteur_1'),
            'ID_Vacation_2':           r.get('ID_Vacation_Enqueteur_2'),
            'Nom_Site_Ou_Aeroport':    r.get('Nom_Aeroport') or '',
            'Date_Vacation':           str(date_v) if date_v else '',
            'Code_Periode_Journee':    r.get('Code_Periode_Journee') or '',
            'Numero_Vacation':         r.get('Numero_Vacation'),
            'Heure_Arrivee_Enqueteur': _time_str(r.get('Heure_Arrivee_Enqueteur')),
            'Heure_Depart_Enqueteur':  _time_str(r.get('Heure_Depart_Enqueteur')),
            'Nbre_Interviews_A_Faire':  r.get('Nbre_Interviews_A_Faire'),
            'Nbre_Interviews_Realisees': r.get('Nbre_Interviews_Realisees'),
            'Nbre_Interviews_Valides':   r.get('Nbre_Interviews_Realisees_Valides'),
            'ID_Personne_1':           r.get('ID_Personne_1'),
            'ID_Personne_2':           r.get('ID_Personne_2'),
            'Libelle_Enqueteur_1':     r.get('Enqueteur_1') or '',
            'Libelle_Enqueteur_2':     r.get('Enqueteur_2') or '',
            'Commentaire_Avant':       r.get('Commentaire_Avant_Vacation'),
            'Commentaire_Apres':       r.get('Commentaire_Apres_Vacation') or r.get('Commentaire_Apres'),
            'Affectation_Modifiable':  bool(r.get('Affectation_Modifiable', False)),
        })
    return result


def get_enqueteurs_pour_affectation(id_vacation_enqueteur: int) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteur_Pour_Affectation_Aeroport(@pID_Vacation_Enqueteur)
    Retourne les candidats qualifiés pour un slot de vacation donné.
    Affecte_Vacation=True : déjà assigné à l'autre slot de la même vacation.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Pour_Affectation_Aeroport(?)",
            (id_vacation_enqueteur,)
        )
        raw_rows = _rows_to_dicts(cursor)
    return [
        {
            'Id_Personne':       r.get('ID_Personne'),
            'Libelle_Enqueteur': r.get('Libelle_Enqueteur') or '',
            'Affecte_Vacation':  bool(r.get('Affecte_Vacation')),
        }
        for r in raw_rows
    ]


def get_enqueteurs_pour_affectation_zone(id_vacation_zone: int) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteur_Pour_Affectation_Zone(@pID_Vacation_Zone)
    Pendant zone de la TVF aéroport, livrée par Philippe le 2026-09-23. Elle
    porte elle-même les règles de sélection et d'exclusion des specs §7.3
    (mission en cours, société de la vacation, enquêteur déjà pris ce jour-là).

    ID_Personne est polymorphe, comme pour Prc_Vacation_Zone_Affectation :
    ID_Personne côté IFOP, ID_Enqueteur_Terrain côté société externe. On le
    transmet tel quel à l'affectation.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Pour_Affectation_Zone(?)",
            (id_vacation_zone,)
        )
        raw_rows = _rows_to_dicts(cursor)
    return [
        {
            'Id_Personne':       r.get('ID_Personne'),
            'Libelle_Enqueteur': r.get('Libelle_Enqueteur') or '',
            'Affecte_Vacation':  bool(r.get('Affecte_Vacation')),
        }
        for r in raw_rows
    ]


def get_tous_enqueteurs(
    date_vacation:      str | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteur_Date_Aeroport — enquêteurs actifs à une date donnée.
    ft_EVER_Liste_Enqueteurs_Aeroport a été supprimée et remplacée par
    ft_EVER_Liste_Enqueteur_Pour_Affectation_Aeroport (per-slot).
    Cette fonction reste pour compatibilité ; le filtre enquêteur de la page
    affectation utilise désormais api_enqueteurs_aeroport directement.
    """
    import datetime
    date_v = date_vacation or datetime.date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Date_Aeroport(?,?,?,NULL,NULL)",
            (id_societe_terrain, date_v, date_v)
        )
        raw_rows = _rows_to_dicts(cursor)
    seen = set()
    result = []
    for r in raw_rows:
        idp = r.get('ID_Personne')
        if idp and idp not in seen:
            seen.add(idp)
            result.append({
                'Id_Personne':       idp,
                'Libelle_Enqueteur': r.get('Libelle_Enqueteur') or '',
            })
    return result


def get_vacations_affectation_hors_aeroport(
    date_vacation:      str,
    id_site:            int | None = None,
    id_personne:        int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_Extranet_Vacation_Zone_Pivot — retourne directement une ligne par vacation
    avec les deux slots enquêteurs déjà pivotés côté SQL.

    Paramètres TVF :
        @pID_Societe_Terrain, @pID_Zone_Enquete(NULL), @pID_Type_Site(NULL),
        @pID_Site, @pDate_Vacation_Debut, @pDate_Vacation_Fin,
        @pNumero_Vacation(NULL), @pID_Enqueteur
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Zone_Pivot(?,NULL,NULL,?,?,?,NULL,?)",
            (id_societe_terrain, id_site, date_vacation, date_vacation, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        t_arr  = r.get('Heure_Arrivee_Enqueteur')
        t_dep  = r.get('Heure_Depart_Enqueteur')
        date_v = r.get('Date_Vacation')
        result.append({
            'ID_Vacation':              r.get('ID_Vacation_Zone_1'),
            'ID_Vacation_1':            r.get('ID_Vacation_Zone_1'),
            'ID_Vacation_2':            r.get('ID_Vacation_Zone_2'),
            'Nom_Site_Ou_Aeroport':     r.get('Zone_Enquete') or '',
            'Date_Vacation':            str(date_v) if date_v else '',
            'Code_Periode_Journee':     '',
            'Numero_Vacation':          r.get('Numero_Vacation'),
            'Heure_Arrivee_Enqueteur':  str(t_arr)[:5] if t_arr else '',
            'Heure_Depart_Enqueteur':   str(t_dep)[:5] if t_dep else '',
            'Nbre_Interviews_A_Faire':  int(r.get('Nbre_Interviews_A_Faire') or 0),
            'Nbre_Interviews_Realisees': int(r.get('Nbre_Interviews_Realisees') or 0),
            'Nbre_Interviews_Valides':  int(r.get('Nbre_Interviews_Realisees_Valides') or 0),
            'ID_Personne_1':            r.get('ID_Enqueteur_1'),
            'ID_Personne_2':            r.get('ID_Enqueteur_2'),
            # Libellés indispensables à l'affichage : sans eux la colonne
            # Enquêteur restait sur « Non affecté » même une fois l'affectation
            # enregistrée (remonté par Nicolas le 29/09). Le pendant aéroport les
            # mappait déjà ; l'oubli ne concernait que les vacations zone.
            'Libelle_Enqueteur_1':      r.get('Enqueteur_1') or '',
            'Libelle_Enqueteur_2':      r.get('Enqueteur_2') or '',
            'Commentaire_Avant':        r.get('Commentaire_Avant_Vacation'),
            'Commentaire_Apres':        r.get('Commentaire_Apres_Vacation'),
            'Affectation_Modifiable':   bool(r.get('Affectation_Modifiable', False)),
        })
    return result


def set_affectation(
    id_vacation: int,
    id_personne: int | None,
) -> bool:
    """
    Prc_Vacation_Aeroport_Affectation(
        @pID_Vacation_Enqueteur  int
        @pID_Personne            int   NULL = désaffectation
        @pMode_Extranet          bit   = 1
    )
    Note : la SP n'expose pas de paramètre @Rang ni @Matricule_Connexion.
    Le CdC prévoit ft_EVER_Set_Affectation avec @Rang et @Id_Personne_Acteur ;
    à câbler dès que Philippe l'aura créé.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Aeroport_Affectation ?,?,?",
                (id_vacation, id_personne, 1)
            )
            conn.commit()
        return True
    except pyodbc.Error as exc:
        logger.error("set_affectation failed id_vacation=%s: %s", id_vacation, exc)
        return False


def set_affectation_hors_aeroport(
    id_vacation_zone: int,
    id_personne:      int | None,
) -> tuple[bool, str]:
    """
    Prc_Vacation_Zone_Affectation(
        @pID_Vacation_Zone  int
        @pID_Personne       int   NULL = désaffectation
        @pMode_Extranet     bit = 1
    )
    La SP retourne un JSON :  [{"ErrorNumber":0,"ErrorMessage":""}]
    SQL Server peut découper le JSON en morceaux de 2033 chars → concaténation.
    Retourne (True, '') ou (False, message_erreur).
    """
    import json as _json
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Zone_Affectation ?,?,1",
                (id_vacation_zone, id_personne)
            )
            # Concaténer les éventuels morceaux JSON
            rows = cursor.fetchall()
            json_str = ''.join(row[0] for row in rows if row and row[0])
            if json_str:
                data = _json.loads(json_str)
                err = data[0] if data else {}
                if err.get('ErrorNumber', 0) != 0:
                    return False, _message_json_output(err)
            conn.commit()
        return True, ''
    except pyodbc.Error as exc:
        logger.error(
            "set_affectation_hors_aeroport failed id_vacation_zone=%s: %s",
            id_vacation_zone, exc
        )
        return False, str(exc)


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

def update_commentaire(
    id_vacation:         int,
    commentaire_vac_1:   str | None,
    commentaire_vol_1:   str | None,
    commentaire_vac_2:   str | None,
    commentaire_vol_2:   str | None,
    matricule_connexion: str | None,
) -> bool:
    """
    Prc_Vacation_Aeroport_Commentaire_Update(
        @pID_Vacation_Vol, @pCommentaire_Vac_Enq_1, @pCommentaire_Vol_Enq_1,
        @pCommentaire_Vac_Enq_2, @pCommentaire_Vol_Enq_2,
        @pUtilisateur_Login, @pMode_Extranet=1
    )
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Aeroport_Commentaire_Update ?,?,?,?,?,?,1",
                (id_vacation, commentaire_vac_1, commentaire_vol_1,
                 commentaire_vac_2, commentaire_vol_2, matricule_connexion)
            )
            conn.commit()
        return True
    except pyodbc.Error as exc:
        logger.error("update_commentaire failed id_vacation=%s: %s", id_vacation, exc)
        return False


def update_commentaire_zone(
    id_vacation_zone_site: int,
    commentaire_vac_zone_1:     str | None,
    commentaire_vac_zonesite_1: str | None,
    commentaire_vac_zone_2:     str | None,
    commentaire_vac_zonesite_2: str | None,
    user_login: str | None,
) -> bool:
    """
    Prc_Vacation_Zone_Commentaire_Update(
        @pID_Vacation_Zone_Site,
        @pCommentaire_Vac_Zone_1, @pCommentaire_Vac_ZoneSite_1,
        @pCommentaire_Vac_Zone_2, @pCommentaire_Vac_ZoneSite_2,
        @pUtilisateur_Login, @pMode_Extranet=1
    )
    Vac_Zone   = commentaire au niveau vacation zone (Vacation_Zone, s'applique à tous les sites)
    Vac_ZoneSite = commentaire au niveau site (Vacation_Zone_Site)
    Comme l'aéroport, la SP met à jour les 2 enquêteurs en un appel → on transmet
    les 4 valeurs (l'appelant préserve l'enquêteur non édité).
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Zone_Commentaire_Update ?,?,?,?,?,?,1",
                (id_vacation_zone_site,
                 commentaire_vac_zone_1, commentaire_vac_zonesite_1,
                 commentaire_vac_zone_2, commentaire_vac_zonesite_2, user_login)
            )
            conn.commit()
        return True
    except pyodbc.Error as exc:
        logger.error("update_commentaire_zone failed id=%s: %s", id_vacation_zone_site, exc)
        return False


# ---------------------------------------------------------------------------
# v1.1 — Enquêteurs Solutions Terrain (§7.2)
# ---------------------------------------------------------------------------

def get_enqueteurs_terrain(id_societe_terrain: int = 2) -> list[dict]:
    """
    Liste des enquêteurs Solutions Terrain (specs §7.2.2, v1.2 §21/08).
    Utilise la TVF ft_Enqueteur_Terrain_Non_IFOP livrée par Philippe le 25/08.

    La TVF a 5 paramètres positionnels (confirmé en base le 28/08, cf.
    bibliothèque SQL v1.9 de Philippe) :
      (@pID_Societe_Terrain, @pID_Enqueteur_Terrain, @pMatricule_Enqueteur_Terrain,
       @pVoxco_User_Creation, @pModeVacation)
    Philippe a ajouté @pVoxco_User_Creation le 26/08 (modify_date de la TVF),
    ce qui a cassé cet appel : l'ancien code ne passait que 4 arguments,
    donc @pModeVacation=0 se retrouvait affecté à @pVoxco_User_Creation,
    provoquant une erreur SQL "nombre d'arguments insuffisant" en prod.
    @pModeVacation=0 : pas besoin de l'historique des vacations pour cet écran.
    La TVF ne filtre pas elle-même sur Date_Fin_Mission ; condition
    d'affichage (specs §7.2.4 règle 02) appliquée ici :
      Date_Fin_Mission IS NULL AND ID_Societe_Terrain = @id_societe_terrain
    Date_Fin_Mission est donc toujours vide pour les lignes renvoyées (mission
    active) — colonne affichée quand même, gérée exclusivement par Philippe
    hors application.

    Voxco_User_Creation / Voxco_User_Date_Creation : statut réel désormais
    livré par Philippe. Aucun paramètre Voxco dans Prc_Enqueteur_Terrain_Non_IFOP_Upsert
    → rien dans l'appli n'écrit cette colonne, elle vient d'ailleurs (probablement
    une synchronisation externe). Exposée ici en LECTURE SEULE (décision du
    2026-08-25, à revoir si Philippe livre un jour un moyen de l'éditer depuis l'appli).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Enqueteur_Terrain_Non_IFOP(?, NULL, NULL, NULL, 0)",
            (id_societe_terrain,)
        )
        rows = _rows_to_dicts(cursor)
    return [
        {
            'ID_Enqueteur_Terrain':            r['ID_Enqueteur_Terrain'],
            'Matricule_Enqueteur_Terrain':      r['Matricule_Enqueteur_Terrain'] or '',
            'Nom':                              r['Nom'] or '',
            'Prenom':                           r['Prenom'] or '',
            'Date_Debut_Mission':               str(r['Date_Debut_Mission']) if r['Date_Debut_Mission'] else '',
            'Date_Fin_Mission':                 str(r['Date_Fin_Mission']) if r['Date_Fin_Mission'] else '',
            'Date_Blocage_IFOP_Affectation':     str(r['Date_Blocage_IFOP_Affectation']) if r['Date_Blocage_IFOP_Affectation'] else '',
            'Motif_Blocage_IFOP_Affectation':    r['Motif_Blocage_IFOP_Affectation'] or '',
            'Voxco_User_Creation':               bool(r['Voxco_User_Creation']),
            'Voxco_User_Date_Creation':          str(r['Voxco_User_Date_Creation']) if r['Voxco_User_Date_Creation'] else '',
        }
        for r in rows
        if r['Date_Fin_Mission'] is None and r['ID_Societe_Terrain'] == id_societe_terrain
    ]


def create_enqueteur_terrain(id_societe_terrain: int, nom: str, prenom: str) -> tuple[bool, str]:
    """
    Prc_Enqueteur_Terrain_Non_IFOP_Upsert(@pID_Societe_Terrain, @pJson,
                                           @pModeExtranet=1, @pJsonOutput OUTPUT)
    Livrée par Philippe le 25/08. Paramètre de sortie (pas un jeu de résultats) :
    appel en batch T-SQL DECLARE/EXEC/SELECT pour le récupérer via pyodbc.

    Création uniquement ici (ID_Enqueteur_Terrain et Matricule_Enqueteur_Terrain
    laissés à null) — la SP génère le matricule, crée le compte Utilisateur, le
    rôle ENQUETEUR et le périmètre aéroport standard en une seule transaction.
    Date_Debut_Mission fixée à aujourd'hui (specs §7.2.5 règle 02 : "création
    date de début de mission", pas un champ saisi par l'utilisateur).

    Renvoie (True, '') ou (False, message_sql) — message déjà en français,
    directement affichable (doublons Nom/Prénom, etc.).
    """
    import json as _json
    import datetime

    payload = [{
        'ID_Enqueteur_Terrain': None,
        'Matricule_Enqueteur_Terrain': None,
        'Nom': nom,
        'Prenom': prenom,
        'Date_Debut_Mission': datetime.date.today().isoformat(),
    }]

    try:
        with get_connection() as conn:
            # La procédure ouvre et referme sa propre transaction. Si on l'appelle
            # à l'intérieur de la nôtre, son ROLLBACK ramène @@TRANCOUNT à 0 et
            # SQL Server lève l'erreur 266 (« nombre d'instructions BEGIN et COMMIT
            # différent »), qui écrase le message métier : l'utilisateur ne voyait
            # plus qu'un « erreur technique » générique. En autocommit, sa
            # transaction fait foi et son message nous parvient via @pJsonOutput.
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(
                """
                DECLARE @out NVARCHAR(MAX);
                EXEC dbo.Prc_Enqueteur_Terrain_Non_IFOP_Upsert
                    @pID_Societe_Terrain=?, @pJson=?, @pModeExtranet=1, @pJsonOutput=@out OUTPUT;
                SELECT @out;
                """,
                (id_societe_terrain, _json.dumps(payload))
            )
            row = cursor.fetchone()

        result = _json.loads(row[0])[0] if row and row[0] else {}
        if result.get('ErrorNumber', 0) != 0:
            return False, _message_json_output(result)
        return True, ''
    except pyodbc.Error as exc:
        logger.error("create_enqueteur_terrain failed: %s", exc)
        return False, _extract_sql_message(exc)



def set_voxco_enqueteur_terrain(
    id_enqueteur_terrain: int,
    actif:                bool,
    id_societe_terrain:   int = 2,
) -> tuple[bool, str]:
    """
    Prc_Enqueteur_Terrain_Non_IFOP_Update_Voxco_Creation(
        @pID_Societe_Terrain, @pID_Enqueteur_Terrain, @pMatricule_Enqueteur_Terrain,
        @pVoxco_User_Insert bit, @pModeExtranet bit, @pJsonOutput OUTPUT)

    Écrit l'état de la case Voxco (§7.2.4 point 7, Nicolas a confirmé le 20/08
    qu'il faut mémoriser l'état coché/décoché). La procédure existe depuis le
    26/08 sur les deux bases ; l'écran l'affichait en lecture seule faute de
    l'avoir repérée.

    Le matricule est laissé à NULL : l'identifiant suffit, et la procédure
    contrôle leur cohérence quand les deux sont fournis.

    Historique (08/10/2026) : la première version de la procédure appliquait la
    valeur à TOUS les enquêteurs de la société ; la correction du matin ignorait
    l'identifiant (réponse « succès », rien d'écrit) ; celle de 11:41 est bonne.
    D'où la relecture finale : on ne confirme jamais un succès qui n'a rien écrit.
    """
    import json as _json
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DECLARE @out NVARCHAR(MAX);
                EXEC dbo.Prc_Enqueteur_Terrain_Non_IFOP_Update_Voxco_Creation
                    @pID_Societe_Terrain=?, @pID_Enqueteur_Terrain=?,
                    @pMatricule_Enqueteur_Terrain=NULL,
                    @pVoxco_User_Insert=?, @pModeExtranet=1, @pJsonOutput=@out OUTPUT;
                SELECT @out;
                """,
                (id_societe_terrain, id_enqueteur_terrain, 1 if actif else 0)
            )
            row = cursor.fetchone()
            conn.commit()

        resultat = _json.loads(row[0])[0] if row and row[0] else {}
        if resultat.get('ErrorNumber', 0) != 0:
            return False, _message_json_output(resultat)

        # Relecture : la procédure peut répondre « succès » sans rien écrire.
        apres = next(
            (e['Voxco_User_Creation'] for e in get_enqueteurs_terrain(id_societe_terrain)
             if e['ID_Enqueteur_Terrain'] == id_enqueteur_terrain),
            None,
        )
        if apres is None or bool(apres) != bool(actif):
            logger.error("set_voxco_enqueteur_terrain: etat non applique id=%s attendu=%s lu=%s",
                         id_enqueteur_terrain, actif, apres)
            return False, "La modification n'a pas été enregistrée."
        return True, ''
    except pyodbc.Error as exc:
        logger.error("set_voxco_enqueteur_terrain failed: %s", exc)
        return False, _extract_sql_message(exc)


# ---------------------------------------------------------------------------
# v1.1 — Vacations Zone (§7.3) — Solutions Terrain
# ---------------------------------------------------------------------------

def get_zones_enquete() -> list[dict]:
    """Référentiel des zones d'enquête (table Zone_Enquete, 46 lignes)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ID_Zone_Enquete, Zone_Enquete FROM dbo.Zone_Enquete ORDER BY Zone_Enquete"
        )
        return [{'ID_Zone_Enquete': r[0], 'Zone_Enquete': r[1]} for r in cursor.fetchall()]


def get_vacations_zone(
    date_debut:         str,
    date_fin:           str,
    id_zone_enquete:    int | None = None,
    id_enqueteur:       int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_Extranet_Vacation_Zone_Pivot(
        @pID_Societe_Terrain, @pID_Zone_Enquete, @pID_Type_Site(NULL),
        @pID_Site(NULL), @pDate_Vacation_Debut, @pDate_Vacation_Fin,
        @pNumero_Vacation(NULL), @pID_Enqueteur
    )
    Écran « Vacations Zone » (specs §7.3.2) : une ligne par vacation, avec les
    deux slots enquêteur déjà pivotés côté SQL. Filtre par ZONE (contrairement à
    l'écran d'affectation général, qui filtre par site).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Zone_Pivot(?,?,NULL,NULL,?,?,NULL,?)",
            (id_societe_terrain, id_zone_enquete, date_debut, date_fin, id_enqueteur)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        date_v = r.get('Date_Vacation')
        result.append({
            'ID_Vacation_Zone_1':      r.get('ID_Vacation_Zone_1'),
            'ID_Vacation_Zone_2':      r.get('ID_Vacation_Zone_2'),
            # Occupant de chaque emplacement + verrou de modification : l'écran
            # permet d'affecter directement depuis la liste (specs §7.3, règle 05).
            'ID_Personne_1':           r.get('ID_Enqueteur_1'),
            'ID_Personne_2':           r.get('ID_Enqueteur_2'),
            'Affectation_Modifiable':  bool(r.get('Affectation_Modifiable')),
            'ID_Zone_Enquete':         r.get('ID_Zone_Enquete'),
            'Zone_Enquete':            r.get('Zone_Enquete') or '',
            'Date_Vacation':           str(date_v) if date_v else '',
            'Numero_Vacation':         r.get('Numero_Vacation'),
            'Nbre_Sites':              r.get('Nbre_Sites'),
            'Nbre_Sites_Gare_Train':   r.get('Nbre_Sites_Gare_Train'),
            # Séparés (pas seulement le libellé combiné) pour l'export CSV (specs §7.3, point 13)
            'Matricule_Enqueteur_1':   r.get('Matricule_Enqueteur_1') or '',
            'Nom_Enqueteur_1':         r.get('Nom_Enqueteur_1') or '',
            'Prenom_Enqueteur_1':      r.get('Prenom_Enqueteur_1') or '',
            'Libelle_Enqueteur_1':     r.get('Enqueteur_1') or '',
            'Matricule_Enqueteur_2':   r.get('Matricule_Enqueteur_2') or '',
            'Nom_Enqueteur_2':         r.get('Nom_Enqueteur_2') or '',
            'Prenom_Enqueteur_2':      r.get('Prenom_Enqueteur_2') or '',
            'Libelle_Enqueteur_2':     r.get('Enqueteur_2') or '',
            'Nbre_Interviews_A_Faire': r.get('Nbre_Interviews_A_Faire'),
            'Vacation_Rattrapage':     bool(r.get('Vacation_Rattrapage')),
        })
    return result


def _insert_vacation_zone_payload(cursor, payload_lignes: list[dict]) -> dict:
    """
    Un appel EXEC Prc_Vacation_Zone_Insert (@pSimulation=0).

    @pJsonOutput est un paramètre de sortie obligatoire depuis le 2026-09-28 :
    on passe donc par un batch DECLARE/EXEC/SELECT pour le récupérer avec pyodbc.
    Il renvoie [{"Creation":n,"Suppression":m}] — le compteur demandé à Philippe
    pour pouvoir distinguer « créé » de « rien fait ».

    Retourne ce dict de compteurs. Peut lever pyodbc.Error.
    """
    import json as _json
    cursor.execute(
        """
        DECLARE @out VARCHAR(MAX);
        EXEC dbo.Prc_Vacation_Zone_Insert
            @pJSON=?, @pVacation_Rattrapage_Only=0, @pSimulation=0, @pJsonOutput=@out OUTPUT;
        SELECT @out;
        """,
        (_json.dumps(payload_lignes),)
    )
    rows = cursor.fetchall()
    brut = ''.join(r[0] for r in rows if r and r[0])
    compteurs = _json.loads(brut)[0] if brut else {}
    return compteurs


def create_vacations_zone(
    id_societe_terrain: int | None,
    lignes:             list[dict],
) -> tuple[bool, str]:
    """
    Prc_Vacation_Zone_Insert(@pJSON, @pVacation_Rattrapage_Only=0, @pSimulation=0,
                             @pJsonOutput OUTPUT)

    lignes : [{'date_vacation': 'YYYY-MM-DD', 'id_zone_enquete': int,
               'nombre_enqueteurs': 1|2}, ...]

    Le nombre d'emplacements enquêteur (1 ou 2) est choisi par l'utilisateur à
    la création (specs v1.2 §7.3.3). Le choix de QUI affecter se fait ensuite
    sur l'écran d'affectation.

    Contrat livré par Philippe le 2026-09-28 : on transmet Nbre_Enqueteurs et on
    laisse Numero_Enqueteur_1 et _2 à NULL — la procédure alloue elle-même ces
    numéros d'emplacement (étiquettes d'emplacement uniques par date et zone,
    société exclue : elle n'est qu'une colonne incluse de l'index unique).
    L'allocation côté procédure est atomique, là où un calcul applicatif
    laisserait une fenêtre entre la lecture des numéros pris et l'insertion.
    C'est ce qui rend possible la règle 07 du §7.3.3 (« autant de vacations que
    souhaité pour une zone à une date donnée »).

    Un appel par ligne, pour pouvoir rattacher une erreur à la ligne fautive.
    Les lignes d'un même lot partagent la transaction.

    Renvoie (True, '') en cas de succès, (False, message) sinon — le message est
    déjà en français (RAISERROR côté SP), affichable directement à l'utilisateur.
    En cas d'échec, rien n'est enregistré : le commit n'a lieu qu'à la fin.
    """
    try:
        creations = 0
        with get_connection() as conn:
            cursor = conn.cursor()
            for ligne in lignes:
                nb_enqueteurs = int(ligne.get('nombre_enqueteurs', 1))
                compteurs = _insert_vacation_zone_payload(cursor, [{
                    'ID_Societe_Terrain':           id_societe_terrain,
                    'Date_Vacation':                ligne['date_vacation'].replace('-', ''),
                    'ID_Zone_Enquete':              int(ligne['id_zone_enquete']),
                    'Nbre_Enqueteurs':              nb_enqueteurs,
                    'Numero_Enqueteur_1':           None,
                    'Numero_Enqueteur_2':           None,
                    'Nombre_Interviews_A_Faire':    None,
                    'ID_Vacation_Zone_A_Rattraper': None,
                }])
                creations += compteurs.get('Creation') or 0
            conn.commit()

        if creations == 0:
            return False, ("Aucune vacation n'a été créée. Elles existent "
                           "peut-être déjà pour ces dates et ces zones.")
        return True, ''
    except pyodbc.Error as exc:
        logger.error("create_vacations_zone failed: %s", exc)
        return False, _extract_sql_message(exc)
