"""
Définition des rôles applicatifs et des droits associés.
Correspondance avec les Code_Role de la base IFOP.
"""

# Codes rôles (valeurs stockées en BDD)
ADMIN_IFOP = 'ADMIN_IFOP'
RESPONSABLE_IFOP = 'RESPONSABLE_IFOP'
RESPONSABLE_ST = 'RESPONSABLE_ST'
SUPERVISEUR_IFOP = 'SUPERVISEUR_IFOP'
SUPERVISEUR_ST = 'SUPERVISEUR_ST'
ENQUETEUR = 'ENQUETEUR'
CLIENT = 'CLIENT'

# Libellés affichés
ROLE_LABELS = {
    ADMIN_IFOP: 'Administrateur IFOP',
    RESPONSABLE_IFOP: 'Responsable terrain IFOP',
    RESPONSABLE_ST: 'Responsable terrain Solutions Terrain',
    SUPERVISEUR_IFOP: 'Superviseur IFOP',
    SUPERVISEUR_ST: 'Superviseur Solutions Terrain',
    ENQUETEUR: 'Enquêteur',
    CLIENT: 'Client',
}

# Page d'accueil par rôle après connexion (specs v1.2, §4.7 — répondu par Nicolas le 2026-08-20)
ROLE_HOME = {
    ADMIN_IFOP: 'core:suivi_aeroport',
    RESPONSABLE_IFOP: 'core:suivi_aeroport',
    RESPONSABLE_ST: 'core:suivi_hors_aeroport',
    SUPERVISEUR_IFOP: 'core:suivi_aeroport',
    SUPERVISEUR_ST: 'core:suivi_hors_aeroport',
    ENQUETEUR: 'core:suivi_aeroport',
    CLIENT: 'core:suivi_aeroport',   # specs : "///" — rôle non utilisé en pratique, valeur de repli
}

# Droits d'accès par fonctionnalité
# True = accès autorisé, False = refusé
DROITS = {
    # Suivi aéroport
    'suivi_aeroport': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: True, CLIENT: True,
    },
    # Suivi hors aéroport
    'suivi_hors_aeroport': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: True, CLIENT: True,
    },
    # Affectation — MODIFIER une affectation (specs §4.8, ligne "Affectation du personnel")
    'affectation': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: False, SUPERVISEUR_ST: False, ENQUETEUR: False, CLIENT: False,
    },
    # Affectation — VOIR l'écran (specs §4.8, lignes "Vue aéroport" / "Vue site") :
    # les superviseurs consultent et filtrent, mais ne peuvent pas modifier une
    # affectation (droit 'affectation' ci-dessus, resté restreint pour eux).
    'affectation_voir': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: False, CLIENT: False,
    },
    # Filtrer par enquêteur dans le suivi
    'filtrer_enqueteur': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: False, CLIENT: False,
    },
    # Ajouter/modifier des commentaires
    'commentaires': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: False, CLIENT: False,
    },
    # Export CSV des tableaux de suivi (l'enquêteur ne voit que ses propres vacations
    # et n'a pas vocation à exporter le terrain)
    'export_csv': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: True, ENQUETEUR: False, CLIENT: True,
    },
    # Visibilité vacations enquêteurs IFOP
    'voir_enqueteurs_ifop': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: False,
        SUPERVISEUR_IFOP: True, SUPERVISEUR_ST: False, ENQUETEUR: True, CLIENT: True,
    },
    # Visibilité vacations enquêteurs Solutions Terrain
    'voir_enqueteurs_st': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: False, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: False, SUPERVISEUR_ST: True, ENQUETEUR: False, CLIENT: True,
    },

    # ---------------------------------------------------------------------
    # v1.1 (specs EVER_2026_Site_Suivi_Affectation_20260821.docx, v1.2) — §7.2 et §7.3
    # Tableau §4.8 confirmé en réunion le 2026-08-21 : SEULS Administrateur IFOP
    # et Responsable Solutions Terrain ont les 3 nouveaux menus. Superviseur ST
    # en a été explicitement retiré au call (il reste en consultation seule,
    # comme pour les aéroports) — Admin ST et Client mis de côté pour l'instant.
    # ---------------------------------------------------------------------

    # Écran « Enquêteurs » (§7.2) — gestion des enquêteurs Solutions Terrain
    'enqueteurs': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: False, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: False, SUPERVISEUR_ST: False, ENQUETEUR: False, CLIENT: False,
    },
    # Écran « Vacations Zone / Affectation » (§7.3)
    'vacations_zone': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: False, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: False, SUPERVISEUR_ST: False, ENQUETEUR: False, CLIENT: False,
    },
}


def has_right(role: str, feature: str) -> bool:
    return DROITS.get(feature, {}).get(role, False)
