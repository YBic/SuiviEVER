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

# Page d'accueil par rôle après connexion
ROLE_HOME = {
    ADMIN_IFOP: 'core:suivi_aeroport',
    RESPONSABLE_IFOP: 'core:suivi_aeroport',
    RESPONSABLE_ST: 'core:suivi_aeroport',
    SUPERVISEUR_IFOP: 'core:suivi_aeroport',
    SUPERVISEUR_ST: 'core:suivi_aeroport',
    ENQUETEUR: 'core:suivi_aeroport',
    CLIENT: 'core:suivi_aeroport',
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
    # Affectation (nécessite en plus le mot de passe ADMIN_PASSWORD)
    'affectation': {
        ADMIN_IFOP: True, RESPONSABLE_IFOP: True, RESPONSABLE_ST: True,
        SUPERVISEUR_IFOP: False, SUPERVISEUR_ST: False, ENQUETEUR: False, CLIENT: False,
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
}


def has_right(role: str, feature: str) -> bool:
    return DROITS.get(feature, {}).get(role, False)
