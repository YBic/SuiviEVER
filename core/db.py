"""
Couche d'accès aux données SQL Server – EVER 2026.

Signatures vérifiées directement sur EVER_DEV le 28/04/2026.

Rappel : TVF → SELECT * FROM dbo.fn(...)   |   SP → EXEC dbo.Prc_...  + commit()
"""
import logging

import pyodbc

from accounts.db import get_connection

logger = logging.getLogger('ever.db')


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
                'ID_Aeroport':   r['ID_Aeroport'],
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
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Date_Aeroport(?,?,?,?,?)",
            (id_societe_terrain, date_vacation, date_vacation, id_aeroport, id_type_vol)
        )
        return _rows_to_dicts(cursor)


def get_sites(date_vacation: str, matricule: str | None = None) -> list[dict]:
    """Hors aéroport — TVF à identifier. Placeholder."""
    return []


def get_enqueteurs_site(date_vacation: str, id_site: int | None = None) -> list[dict]:
    """Hors aéroport — TVF à identifier. Placeholder."""
    return []


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
    ft_EVER_Tableau_Chef_Equipe(
        @pUtilisateur_Login     varchar  NULL ok   ← login session (pas matricule)
        @pID_Societe_Terrain    tinyint  NULL ok
        @pDate_Vol              date     NULL ok
        @pID_Aeroport           smallint NULL ok
        @pID_Type_Vacation_Vol  tinyint  NULL ok
        @pID_ENPA_VolSplit      int      NULL ok   ← toujours NULL côté web
        @pID_Personne           int      NULL ok
        @pDuree_Minute_Cloture  int      NULL ok   ← toujours NULL côté web
    )
    Colonnes clés : 'Ordre_Tri', 'Date du Vol', 'N° Vacation', 'Enquêteur',
                    'N° Vol', 'Destination', 'Taux de réalisation', ...
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Chef_Equipe(?,?,?,?,?,NULL,?,NULL)",
            (user_login, id_societe_terrain, date_vacation, id_aeroport, id_type_vol, id_personne)
        )
        return _rows_to_dicts(cursor)


# ---------------------------------------------------------------------------
# Tableau de suivi hors aéroport
# ---------------------------------------------------------------------------

def get_suivi_hors_aeroport(
    date_vacation:      str,
    id_site:            int | None = None,
    id_personne:        int | None = None,
    id_societe_terrain: int | None = None,
) -> list[dict]:
    """
    ft_Vacation_Enqueteur_Tdb_Suivi — signature à confirmer.
    TODO: câbler une fois les paramètres validés.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Vacation_Enqueteur_Tdb_Suivi(?,?,?,?)",
            (id_societe_terrain, date_vacation, id_site, id_personne)
        )
        return _rows_to_dicts(cursor)


def get_detail_vacation_hors_aeroport(id_vacation: int) -> list[dict]:
    """TODO: TVF hors aéroport à identifier."""
    return []


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
        @pID_Aeroport           ...
        @pDate_Vacation_Debut   date
        @pDate_Vacation_Fin     date
        @pNumero_Vacation       ...      NULL
        @pID_Personne           int      NULL ok
    )
    TODO: signature exacte à confirmer.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Aeroport_Pivot(?,?,?,?,NULL,?)",
            (id_societe_terrain, id_aeroport, date_vacation, date_vacation, id_personne)
        )
        return _rows_to_dicts(cursor)


def get_tous_enqueteurs(id_societe_terrain: int | None = None) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteurs_Aeroport(
        @pID_Societe_Terrain  tinyint  NULL ok
        @pMatricule           varchar  NULL ok
    )
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteurs_Aeroport(?,NULL)",
            (id_societe_terrain,)
        )
        return _rows_to_dicts(cursor)


def set_affectation(
    id_vacation:         int,
    rang:                int,
    id_personne:         int | None,
    matricule_connexion: str | None,
) -> bool:
    """
    Prc_Vacation_Aeroport_Affectation
    TODO: signature complète à confirmer avec Philippe.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Aeroport_Affectation ?,?,?,?",
                (id_vacation, id_personne, 1, matricule_connexion)
            )
            conn.commit()
        return True
    except pyodbc.Error as exc:
        logger.error("set_affectation failed id_vacation=%s: %s", id_vacation, exc)
        return False


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

def update_commentaire(
    id_vacation:         int,
    commentaire_avant:   str | None,
    commentaire_apres:   str | None,
    matricule_connexion: str | None,
) -> bool:
    """
    Prc_Vacation_Aeroport_Commentaire_Update(
        @pID_Vacation_Vol, @pCommentaire_Vac_Enq_1, @pCommentaire_Vol_Enq_1,
        @pCommentaire_Vac_Enq_2=NULL, @pCommentaire_Vol_Enq_2=NULL,
        @pMatricule_Connexion, @pMode_Extranet=1
    )
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Aeroport_Commentaire_Update ?,?,?,NULL,NULL,?,1",
                (id_vacation, commentaire_avant, commentaire_apres, matricule_connexion)
            )
            conn.commit()
        return True
    except pyodbc.Error as exc:
        logger.error("update_commentaire failed id_vacation=%s: %s", id_vacation, exc)
        return False
