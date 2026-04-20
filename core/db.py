"""
Couche d'accès aux données SQL Server – EVER 2026.

Toutes les fonctions ci-dessous sont des PLACEHOLDERS en attente du
câblage réel avec les objets SQL livrés par l'équipe BDD.

Objets SQL attendus (noms et signatures à confirmer) :
  TVF  ft_EVER_Liste_Periode_Terrain       → périodes terrain
  TVF  ft_EVER_Liste_Aeroports             → aéroports par date/société
  TVF  ft_EVER_Liste_Enqueteur_Date_Aeroport → enquêteurs par date/aéroport
  TVF  ft_EVER_Liste_Enqueteurs            → liste complète enquêteurs
  TVF  ft_EVER_Tableau_Chef_Equipe         → suivi aéroport (chef d'équipe)
  SP   Prc_Vacation_Affectation            → affecter un enquêteur
  SP   Prc_Vacation_Commentaire_Update     → mettre à jour les commentaires

Note : les TVFs s'appellent avec SELECT * FROM dbo.fn(...), pas avec EXEC.
"""
import pyodbc
from accounts.db import get_connection


def _rows_to_dicts(cursor) -> list[dict]:
    """Convertit les lignes d'un curseur pyodbc en liste de dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Listes de référence (filtres / menus déroulants)
# ---------------------------------------------------------------------------

def get_periodes() -> list[dict]:
    """
    Retourne les périodes terrain disponibles.
    TVF : ft_EVER_Liste_Periode_Terrain(@pID_Periode_Terrain, @pDate_Debut, @pDate_Fin, @pID_Vague)
    TODO: câbler les vrais paramètres une fois la SP livrée.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Periode_Terrain(NULL, NULL, NULL, NULL)"
        )
        return _rows_to_dicts(cursor)


def get_aeroports(date_vacation: str, matricule: str | None = None) -> list[dict]:
    """
    Retourne les aéroports ayant des vacations à la date donnée.
    TVF : ft_EVER_Liste_Aeroports(@pID_Societe_Terrain, @pDate_Debut, @pDate_Fin, @pMatricule)
    TODO: câbler id_societe_terrain depuis la session.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Aeroports(NULL, ?, ?, ?)",
            (date_vacation, date_vacation, matricule)
        )
        return _rows_to_dicts(cursor)


def get_sites(date_vacation: str, matricule: str | None = None) -> list[dict]:
    """
    Retourne les sites hors aéroport ayant des vacations à la date donnée.
    TODO: identifier la TVF correspondante côté BDD.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Aeroports(NULL, ?, ?, ?)",
            (date_vacation, date_vacation, matricule)
        )
        return _rows_to_dicts(cursor)


def get_enqueteurs_aeroport(date_vacation: str, id_aeroport: int | None = None) -> list[dict]:
    """
    Retourne les enquêteurs affectés en aéroport à la date/aéroport donnés.
    TVF : ft_EVER_Liste_Enqueteur_Date_Aeroport(@pID_Societe_Terrain, @pDate_Debut, @pDate_Fin,
                                                 @pID_Aeroport, @pID_Type_Vacation_Vol)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Date_Aeroport(NULL, ?, ?, ?, NULL)",
            (date_vacation, date_vacation, id_aeroport)
        )
        return _rows_to_dicts(cursor)


def get_enqueteurs_site(date_vacation: str, id_site: int | None = None) -> list[dict]:
    """
    Retourne les enquêteurs affectés sur les sites hors aéroport.
    TODO: identifier la TVF correspondante côté BDD.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteurs(NULL, NULL)"
        )
        return _rows_to_dicts(cursor)


# ---------------------------------------------------------------------------
# Données de suivi aéroport
# ---------------------------------------------------------------------------

def get_suivi_aeroport(
    date_vacation: str,
    id_aeroport:   int  | None = None,
    id_personne:   int  | None = None,
    id_type_vol:   int  | None = None,
    role:          str         = 'ENQUETEUR',
) -> list[dict]:
    """
    Retourne les données de suivi pour les vacations en aéroport.
    TVF : ft_EVER_Tableau_Chef_Equipe(@pMatricule_Connexion, @pDate_Vol, @pID_Aeroport,
                                       @pID_Type_Vacation_Vol, @pID_ENPA_VolSplit,
                                       @pID_Personne, @pDuree_Minute_Cloture)
    TODO: adapter les paramètres (matricule_connexion depuis session, durée cloture).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Chef_Equipe(NULL, ?, ?, ?, NULL, ?, NULL)",
            (date_vacation, id_aeroport, id_type_vol, id_personne)
        )
        return _rows_to_dicts(cursor)


# ---------------------------------------------------------------------------
# Données de suivi hors aéroport
# ---------------------------------------------------------------------------

def get_suivi_hors_aeroport(
    date_vacation: str,
    id_site:       int | None = None,
    id_personne:   int | None = None,
    role:          str        = 'ENQUETEUR',
) -> list[dict]:
    """
    Retourne les données de suivi pour les vacations hors aéroport.
    TODO: identifier la TVF correspondante côté BDD.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Enqueteur(NULL, ?)",
            (date_vacation,)
        )
        return _rows_to_dicts(cursor)


def get_detail_vacation_hors_aeroport(id_vacation: int) -> list[dict]:
    """
    Retourne le détail des sites composant une vacation multi-sites.
    TODO: identifier la TVF correspondante côté BDD.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteur_Pour_Affectation(?)",
            (id_vacation,)
        )
        return _rows_to_dicts(cursor)


# ---------------------------------------------------------------------------
# Données d'affectation
# ---------------------------------------------------------------------------

def get_vacations_affectation(
    date_vacation: str,
    id_aeroport:   int | None = None,
    id_site:       int | None = None,
    id_personne:   int | None = None,
) -> list[dict]:
    """
    Retourne les vacations avec leurs enquêteurs affectés.
    TVF : ft_Extranet_Vacation_Enqueteur_Pivot(@pID_Societe_Terrain, @pID_Aeroport,
                                                @pDate_Vacation_Debut, @pDate_Vacation_Fin,
                                                @pNumero_Vacation, @pID_Personne)
    TODO: câbler les paramètres.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Enqueteur_Pivot(NULL, ?, ?, ?, NULL, ?)",
            (id_aeroport, date_vacation, date_vacation, id_personne)
        )
        return _rows_to_dicts(cursor)


def get_tous_enqueteurs() -> list[dict]:
    """
    Retourne la liste complète des enquêteurs pour les menus d'affectation.
    TVF : ft_EVER_Liste_Enqueteurs(@pID_Societe_Terrain, @pMatricule)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dbo.ft_EVER_Liste_Enqueteurs(NULL, NULL)")
        return _rows_to_dicts(cursor)


def set_affectation(
    id_vacation:        int,
    rang:               int,
    id_personne:        int | None,
    id_personne_acteur: int,
) -> bool:
    """
    Affecte (ou désaffecte si id_personne=None) un enquêteur à une vacation.
    SP : Prc_Vacation_Affectation(@pID_Vacation_Enqueteur, @pID_Personne, @pMode_Extranet)
    TODO: adapter rang → ID_Vacation_Enqueteur correct, et pMode_Extranet.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Affectation ?, ?, ?",
                (id_vacation, id_personne, 0)
            )
            conn.commit()
        return True
    except pyodbc.Error:
        return False


# ---------------------------------------------------------------------------
# Commentaires
# ---------------------------------------------------------------------------

def update_commentaire(
    id_vacation:        int,
    commentaire_avant:  str | None,
    commentaire_apres:  str | None,
    id_personne_acteur: int,
) -> bool:
    """
    Met à jour les commentaires avant/après vacation.
    SP : Prc_Vacation_Commentaire_Update(@pID_Vacation_Vol, @pCommentaire_Vac_Enq_1,
                                          @pCommentaire_Vol_Enq_1, @pCommentaire_Vac_Enq_2,
                                          @pCommentaire_Vol_Enq_2, @pMatricule_Connexion,
                                          @pMode_Extranet)
    TODO: câbler matricule_connexion depuis session.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "EXEC dbo.Prc_Vacation_Commentaire_Update ?, ?, ?, NULL, NULL, NULL, 0",
                (id_vacation, commentaire_avant, commentaire_apres)
            )
            conn.commit()
        return True
    except pyodbc.Error:
        return False
