"""
Vues d'authentification – EVER 2026.

Flux :
    /login/         → formulaire login + mot de passe
                      → si Mot_De_Passe_Hash NULL en base : redirect /set-password/
                      → sinon : authentification normale
    /set-password/  → formulaire de création du mot de passe (première connexion)
    /logout/        → destruction de session, redirect /login/

La session stocke :
    user_id                  int   – ID_Utilisateur
    user_login               str   – identifiant de connexion
    user_nom                 str   – "Prénom NOM"
    user_role                str   – code rôle (ADMIN_IFOP, RESPONSABLE_IFOP, …)
    user_role_label          str   – libellé du rôle
    user_id_societe_terrain  int   – 1=IFOP / 2=ST / None pour les rôles non liés à une société
    user_code_societe_terrain str  – "IFOP" / "SOLUTION_TERRAIN" / None
    user_matricule           str   – matricule enquêteur (@pMatricule_Connexion), peut être None
    affectation_authorized   bool  – mot de passe section affectation validé
"""

import logging

from django.shortcuts import render, redirect
from django.contrib import messages

from accounts.roles import ROLE_LABELS, ROLE_HOME
from accounts import db
from accounts.db import AuthResult

logger = logging.getLogger('ever.auth')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request) -> str:
    """Retourne l'IP du client (gère les proxies via X-Forwarded-For)."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '?')


def _build_session(request, user: dict, login: str):
    """Remplit la session à partir du dict utilisateur retourné par ft_EVER_Liste_Utilisateur."""
    role   = user.get('Code_Role', 'ENQUETEUR')
    prenom = (user.get('Prenom') or '').strip().title()
    nom    = (user.get('Nom')    or '').strip().upper()

    request.session['user_id']                   = user.get('ID_Utilisateur')
    request.session['user_login']                = login
    request.session['user_nom']                  = f"{prenom} {nom}".strip()
    request.session['user_role']                 = role
    request.session['user_role_label']           = ROLE_LABELS.get(role, role)
    request.session['user_id_societe_terrain']   = user.get('ID_Societe_Terrain')
    request.session['user_code_societe_terrain'] = user.get('Code_Societe_Terrain')
    request.session['affectation_authorized']    = False

    # Matricule enquêteur (utilisé comme @pMatricule_Connexion dans les fonctions de suivi)
    matricule = db.get_matricule_enqueteur(login)
    request.session['user_matricule'] = matricule


def _validate_new_password(password: str, confirm: str) -> list[str]:
    """
    Valide les règles de composition du mot de passe.
    Retourne une liste d'erreurs (vide = OK).
    """
    errors = []
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères.")
    if password != confirm:
        errors.append("Les deux mots de passe ne correspondent pas.")
    if not any(c.isdigit() for c in password):
        errors.append("Le mot de passe doit contenir au moins un chiffre.")
    if not any(c.isalpha() for c in password):
        errors.append("Le mot de passe doit contenir au moins une lettre.")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        errors.append("Le mot de passe doit contenir au moins un caractère spécial.")
    return errors


# ---------------------------------------------------------------------------
# Vue : connexion
# ---------------------------------------------------------------------------

def login_view(request):
    """
    Page de connexion.
    POST : tente l'authentification.
      - Login inconnu     → message d'erreur, reste sur /login/
      - Première connexion → mémorise le login en session temporaire, redirect /set-password/
      - Mot de passe OK   → session complète, redirect page d'accueil selon rôle
      - Mauvais mdp       → message d'erreur, reste sur /login/
    """
    if request.session.get('user_login'):
        return redirect('core:suivi_aeroport')

    if request.method != 'POST':
        return render(request, 'accounts/login.html')

    login    = request.POST.get('login', '').strip()
    password = request.POST.get('password', '').strip()
    ip       = _get_ip(request)

    if not login or not password:
        messages.error(request, "Veuillez renseigner votre identifiant et votre mot de passe.")
        return render(request, 'accounts/login.html')

    result, user = db.authenticate(login, password)

    if result == AuthResult.UNKNOWN:
        logger.warning("LOGIN_UNKNOWN  login=%-20s ip=%s", login, ip)
        messages.error(request, "Identifiant inconnu.")
        return render(request, 'accounts/login.html')

    if result == AuthResult.FIRST_LOGIN:
        logger.info("LOGIN_FIRST    login=%-20s ip=%s  role=%s", login, ip, user.get('Code_Role'))
        # Première connexion : on ne crée pas encore de session complète.
        # On mémorise le login + données utilisateur en session temporaire.
        request.session['pending_login'] = login
        request.session['pending_user']  = {
            k: v for k, v in user.items()
            if isinstance(v, (str, int, float, bool, type(None)))
        }
        return redirect('accounts:set_password')

    if result == AuthResult.BAD_PASSWORD:
        logger.warning("LOGIN_BAD_PWD  login=%-20s ip=%s", login, ip)
        messages.error(request, "Mot de passe incorrect.")
        return render(request, 'accounts/login.html')

    # result == AuthResult.OK
    logger.info("LOGIN_OK       login=%-20s ip=%s  role=%s", login, ip, user.get('Code_Role'))
    _build_session(request, user, login)
    home = ROLE_HOME.get(user.get('Code_Role', ''), 'core:suivi_aeroport')
    return redirect(home)


# ---------------------------------------------------------------------------
# Vue : définition du mot de passe (première connexion)
# ---------------------------------------------------------------------------

def set_password_view(request):
    """
    Affiché uniquement si la session contient 'pending_login'
    (utilisateur dont le mot de passe n'a jamais été défini).

    POST : valide les règles, enregistre le hash en base, ouvre la session, redirige.
    """
    login = request.session.get('pending_login')
    if not login:
        return redirect('accounts:login')

    if request.method != 'POST':
        prenom = (request.session.get('pending_user', {}).get('Prenom') or '').title()
        return render(request, 'accounts/set_password.html', {'prenom': prenom})

    password = request.POST.get('password', '')
    confirm  = request.POST.get('confirm', '')
    errors   = _validate_new_password(password, confirm)
    ip       = _get_ip(request)

    if errors:
        prenom = (request.session.get('pending_user', {}).get('Prenom') or '').title()
        for e in errors:
            messages.error(request, e)
        return render(request, 'accounts/set_password.html', {'prenom': prenom})

    ok = db.set_password(login, password)
    if not ok:
        logger.error("SET_PASSWORD_FAIL  login=%-20s ip=%s", login, ip)
        messages.error(request, "Erreur lors de l'enregistrement du mot de passe. Contactez l'administrateur.")
        prenom = (request.session.get('pending_user', {}).get('Prenom') or '').title()
        return render(request, 'accounts/set_password.html', {'prenom': prenom})

    logger.info("SET_PASSWORD_OK    login=%-20s ip=%s", login, ip)

    # Mot de passe enregistré → ouvrir la session complète
    user = request.session.pop('pending_user', {})
    request.session.pop('pending_login', None)
    _build_session(request, user, login)

    messages.success(request, "Mot de passe créé avec succès. Bienvenue !")
    home = ROLE_HOME.get(user.get('Code_Role', ''), 'core:suivi_aeroport')
    return redirect(home)


# ---------------------------------------------------------------------------
# Vue : déconnexion
# ---------------------------------------------------------------------------

def logout_view(request):
    """Détruit la session et redirige vers /login/."""
    login = request.session.get('user_login', '?')
    ip    = _get_ip(request)
    logger.info("LOGOUT             login=%-20s ip=%s", login, ip)
    request.session.flush()
    return redirect('accounts:login')
