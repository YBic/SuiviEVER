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

    Notes :
    - La TVF retourne un résultat "enrichi" : lignes vacation + lignes total vol
      + lignes total aéroport. On filtre sur ID_Vacation_Vol IS NOT NULL pour
      ne garder que les lignes vacation (le JS calcule ses propres totaux).
    - Les noms de colonnes sont en français avec espaces/accents ; on les normalise
      ici pour que le JS reste indépendant de l'implémentation SQL.
    - Le code IATA compagnie est extrait du numéro de vol (ex: "U2" de "U2-4427").
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Tableau_Chef_Equipe(?,?,?,?,?,NULL,?,NULL)",
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
            code_aero = r.get('Code Aéroport Départ') or ''
            id_aero   = r.get('ID_Aeroport')
            num_vol   = r.get('N° Vol') or ''
            # Code IATA = partie avant le "-" (ex: "U2" pour "U2-4427")
            code_iata = num_vol.split('-')[0] if '-' in num_vol else ''
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
                'Objectif':               r.get('Objectif Questionnaires') or 0,
                'Completes_100':          r.get('100% Completés') or 0,
                'Recrutes':               r.get('Recrutés') or 0,
                'Questionnaires_Valides': r.get('Completés Questions FAF') or 0,
                'Abandons':               r.get('Abandon') or 0,
                'Statut_Vol':             r.get('STATUT VOL') or '',
                'Commentaire_Vacation':   r.get('Commentaires_Vacation'),
                'Commentaire_Vol':        r.get('Commentaires_Vacation_Vol'),
            })
        return result


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
    ft_Extranet_Vacation_Zone(
        @pID_Societe_Terrain  tinyint  NULL ok
        @pID_Vacation_Zone    int      NULL ok
        @pID_Zone_Enquete     smallint NULL ok   ← id_site
        @pID_Type_Site        tinyint  NULL ok
        @pID_Site             smallint NULL ok
        @pDate_Vacation_Debut date     NULL ok
        @pDate_Vacation_Fin   date     NULL ok
        @pNumero_Enqueteur    tinyint  NULL ok
        @pNumero_Vacation     tinyint  NULL ok
        @pID_Enqueteur        int      NULL ok   ← id_personne
    )
    Retourne une ligne par (vacation × enquêteur). On garde uniquement
    Numero_Enqueteur=1 pour éviter le double-comptage des objectifs.
    Normalisation des colonnes SQL → clés JSON attendues par le JS.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_Extranet_Vacation_Zone(?,NULL,?,NULL,NULL,?,?,NULL,NULL,?)",
            (id_societe_terrain, id_site, date_vacation, date_vacation, id_personne)
        )
        raw_rows = _rows_to_dicts(cursor)

    # Garder le rang principal (Numero_Enqueteur=1) pour éviter les doublons
    # Si la colonne est NULL (pas encore d'enquêteur affecté), on garde la ligne quand même
    rows = [r for r in raw_rows if (r.get('Numero_Enqueteur') or 1) == 1]

    result = []
    for r in rows:
        date_v   = r.get('Date_Vacation')
        objectif = int(r.get('Nbre_Interviews_A_Faire') or 0)
        recrutes = int(r.get('Nbre_Interviews_Realisees') or 0)
        valides  = int(r.get('Nbre_Interviews_Realisees_Valides') or 0)
        result.append({
            'Id_Site':               r.get('ID_Zone_Enquete'),
            'Nom_Site':              r.get('Zone_Enquete') or '',
            'Type_Site':             'ZONE',
            'ID_Vacation':           r.get('ID_Vacation_Zone'),
            'Numero_Vacation':       r.get('Numero_Vacation'),
            'Libelle_Enqueteur':     r.get('Enqueteur') or '',
            'Date_Vacation':         str(date_v) if date_v else '',
            'Objectif':              objectif,
            'Completes_100':         valides,
            'Recrutes':              recrutes,
            'Questionnaires_Valides': int(r.get('Nbre_Interviews_FAF_Realisees_Valides') or 0),
            'Abandons':              max(0, recrutes - valides),
            'Commentaire_Vacation':  r.get('Commentaire_Avant_Vacation'),
            'Affectation_Modifiable': bool(r.get('Affectation_Modifiable', False)),
        })
    return result


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
        @pID_Aeroport           smallint NULL ok
        @pDate_Vacation_Debut   date
        @pDate_Vacation_Fin     date
        @pNumero_Vacation       varchar  NULL
        @pID_Personne           int      NULL ok
    )
    Colonnes retournées (noms SQL) → clés JSON normalisées :
      ID_Vacation_Enqueteur_1    → ID_Vacation
      Nom_Aeroport               → Nom_Site_Ou_Aeroport
      Date_Vacation (date obj)   → Date_Vacation (str YYYY-MM-DD)
      Heure_Arrivee/Depart (time)→ str HH:MM
      Nbre_Interviews_Realisees_Valides → Nbre_Interviews_Valides
      Commentaire_Avant_Vacation → Commentaire_Avant
      Commentaire_Apres_Vacation → Commentaire_Apres (ou Apres_Vacation si absent)
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
            'Commentaire_Avant':       r.get('Commentaire_Avant_Vacation'),
            'Commentaire_Apres':       r.get('Commentaire_Apres_Vacation') or r.get('Commentaire_Apres'),
            'Affectation_Modifiable':  bool(r.get('Affectation_Modifiable', False)),
        })
    return result


def get_tous_enqueteurs(id_societe_terrain: int | None = None) -> list[dict]:
    """
    ft_EVER_Liste_Enqueteurs_Aeroport(
        @pID_Societe_Terrain  tinyint  NULL ok
        @pMatricule           varchar  NULL ok
    )
    Colonnes retournées : Matricule, ID_Personne, Nom, Prenom, ID_Role, Code_Role
    → normalisées en Id_Personne + Libelle_Enqueteur pour le JS.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM dbo.ft_EVER_Liste_Enqueteurs_Aeroport(?,NULL)",
            (id_societe_terrain,)
        )
        raw_rows = _rows_to_dicts(cursor)

    result = []
    for r in raw_rows:
        matricule = r.get('Matricule') or ''
        nom       = r.get('Nom') or ''
        prenom    = r.get('Prenom') or ''
        result.append({
            'Id_Personne':       r.get('ID_Personne'),
            'Libelle_Enqueteur': f"{matricule} – {prenom} {nom}".strip(' –'),
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
