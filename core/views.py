"""
Vues principales de l'application EVER.
Architecture AJAX-driven : les pages rendent le squelette HTML,
les données sont chargées dynamiquement via les endpoints /api/*.
"""
import json
import logging
import uuid
from datetime import date

from django.shortcuts import render
from django.http import JsonResponse as _BaseJsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings


class JsonResponse(_BaseJsonResponse):
    """JsonResponse avec DjangoJSONEncoder par défaut (gère datetime, time, Decimal…)."""
    def __init__(self, data, encoder=DjangoJSONEncoder, **kwargs):
        super().__init__(data, encoder=encoder, **kwargs)

from .decorators import login_required, require_right
from accounts.roles import has_right
from . import db

logger = logging.getLogger('ever.views')


def _api_error(request, exc) -> JsonResponse:
    """
    Réponse d'erreur technique sans fuite d'information (audit sécurité 2026).

    Le message brut de pyodbc expose la version du driver ODBC et le nom des
    objets SQL appelés. Il part désormais dans app.log, indexé par une référence
    courte ; le client ne reçoit que cette référence, à citer au support.

    ⚠️ Ne pas utiliser pour les erreurs MÉTIER : celles-ci remontent déjà par les
    tuples (False, message) de core.db, et leur texte est écrit pour l'utilisateur.
    """
    ref = uuid.uuid4().hex[:8]
    logger.exception('[%s] %s %s : %s', ref, request.method, request.path, exc)
    return JsonResponse(
        {
            'status':  'error',
            'message': f"Une erreur technique est survenue. "
                       f"Merci de communiquer la référence {ref} au support.",
            'ref':     ref,
        },
        status=500,
    )


# ---------------------------------------------------------------------------
# Helpers de session
# ---------------------------------------------------------------------------

def _session_ctx(request) -> dict:
    """
    Retourne les valeurs de session fréquemment utilisées dans les vues API.
    Centralise l'extraction pour éviter la répétition.

    Note : les TVFs SQL filtrent par id_societe_terrain pour les sociétés terrain
    externes. Pour les comptes IFOP (Code_Societe_Terrain='IFOP'), passer NULL
    déclenche le "voir tout" dans les TVFs — passer 1 (ID IFOP) ne matche rien.
    """
    code_st = request.session.get('user_code_societe_terrain', '')
    id_st   = None if code_st == 'IFOP' else request.session.get('user_id_societe_terrain')
    return {
        'role':               request.session.get('user_role', 'ENQUETEUR'),
        'user_id':            request.session.get('user_id'),
        'user_login':         request.session.get('user_login'),
        'matricule':          request.session.get('user_matricule'),
        'id_societe_terrain': id_st,
    }


def _enqueteur_id_personne(request, ctx) -> int | None:
    """
    ID_Personne de l'enquêteur connecté, résolu depuis son matricule et mis en
    cache en session. ⚠️ user_id (session) = ID_Utilisateur (compte de connexion),
    PAS l'ID_Personne attendu par @pID_Personne dans les TVFs — d'où cette résolution.
    """
    idp = request.session.get('user_id_personne')
    if idp:
        return idp
    idp = db.get_id_personne_by_matricule(ctx['matricule'], ctx['id_societe_terrain'])
    if idp:
        request.session['user_id_personne'] = idp
    return idp


# ---------------------------------------------------------------------------
# Pages principales
# ---------------------------------------------------------------------------

def _nav_rights(role: str) -> dict:
    """
    Droits communs affichés dans le header (partagé par toutes les pages) :
    chaque vue doit les inclure dans son contexte pour que la navigation
    reflète les accès réels, quelle que soit la page affichée.

    can_affectation = DROIT DE VOIR l'écran (specs §4.8 "Vue aéroport"/"Vue site") ;
    c'est lui qui gouverne l'icône de navigation. Le droit de MODIFIER une
    affectation ('affectation' strict) est plus restrictif et n'est exposé qu'à
    la page affectation elle-même, sous can_affectation_modifier.
    """
    return {
        'can_affectation':   has_right(role, 'affectation_voir'),
        'can_enqueteurs':    has_right(role, 'enqueteurs'),
        'can_vacations_zone': has_right(role, 'vacations_zone'),
    }


@login_required
def suivi_aeroport(request):
    """Page de suivi des vacations en aéroport."""
    role = request.session.get('user_role', '')
    context = {
        'page':                 'suivi_aeroport',
        'can_filter_enqueteur': has_right(role, 'filtrer_enqueteur'),
        'can_comment':          has_right(role, 'commentaires'),
        'can_export':           has_right(role, 'export_csv'),
        'today':                date.today(),
        **_nav_rights(role),
    }
    return render(request, 'core/suivi_aeroport.html', context)


@login_required
def suivi_hors_aeroport(request):
    """Page de suivi des vacations hors aéroport."""
    role = request.session.get('user_role', '')
    context = {
        'page':                 'suivi_hors_aeroport',
        'can_filter_enqueteur': has_right(role, 'filtrer_enqueteur'),
        'can_comment':          has_right(role, 'commentaires'),
        'can_export':           has_right(role, 'export_csv'),
        'today':                date.today(),
        **_nav_rights(role),
    }
    return render(request, 'core/suivi_hors_aeroport.html', context)


@require_right('affectation_voir')
def affectation(request):
    """
    Page d'affectation des enquêteurs aux vacations.
    Accessible en LECTURE aux superviseurs (§4.8 "Vue aéroport"/"Vue site") ;
    seuls Admin/Responsables peuvent réellement modifier une affectation
    (can_affectation_modifier, contrôlé aussi côté API par api_set_affectation).
    """
    role = request.session.get('user_role', '')
    context = {
        'page':                      'affectation',
        'today':                     date.today(),
        'can_affectation_modifier':  has_right(role, 'affectation'),
        **_nav_rights(role),
    }
    return render(request, 'core/affectation.html', context)


@require_right('enqueteurs')
def enqueteurs(request):
    """Page de gestion des enquêteurs Solutions Terrain (v1.1, §7.2)."""
    role = request.session.get('user_role', '')
    context = {'page': 'enqueteurs', **_nav_rights(role)}
    return render(request, 'core/enqueteurs.html', context)


@require_right('vacations_zone')
def vacations_zone(request):
    """Page Vacations Zone / Affectation — Solutions Terrain (v1.1, §7.3)."""
    role = request.session.get('user_role', '')
    context = {
        'page':                     'vacations_zone',
        'today':                    date.today(),
        # L'affectation se fait aussi depuis cette liste (§7.3, règle 05) : même
        # droit que sur l'écran Affectation.
        'can_affectation_modifier': has_right(role, 'affectation'),
        **_nav_rights(role),
    }
    return render(request, 'core/vacations_zone.html', context)


# ---------------------------------------------------------------------------
# API AJAX – Listes de référence
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_types_vol(request):
    try:
        data = db.get_types_vol()
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_periodes(request):
    try:
        data = db.get_periodes()
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_aeroports(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    try:
        data = db.get_aeroports(
            date_vacation,
            user_login=ctx['user_login'],
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_sites(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_personne   = None
    if ctx['role'] == 'ENQUETEUR':
        id_personne = _enqueteur_id_personne(request, ctx)
        if not id_personne:
            return JsonResponse({'status': 'ok', 'data': []})
    try:
        data = db.get_sites(
            date_vacation,
            id_societe_terrain=ctx['id_societe_terrain'],
            id_personne=id_personne,
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_enqueteurs_aeroport(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_aeroport   = request.GET.get('id_aeroport') or None
    try:
        data = db.get_enqueteurs_aeroport(
            date_vacation,
            id_aeroport=id_aeroport,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_enqueteurs_site(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_site       = request.GET.get('id_site') or None
    try:
        data = db.get_enqueteurs_site(
            date_vacation,
            id_site=id_site,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


# ---------------------------------------------------------------------------
# API AJAX – Données de suivi
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_suivi_aeroport(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_aeroport   = int(v) if (v := request.GET.get('id_aeroport') or None) else None
    id_personne   = int(v) if (v := request.GET.get('id_personne') or None) else None
    id_type_vol   = int(v) if (v := request.GET.get('id_type_vol') or None) else None

    # Un enquêteur ne voit que ses propres vacations : @pID_Personne est forcé sur
    # l'enquêteur connecté et doit toujours être renseigné (sinon il verrait tout).
    if ctx['role'] == 'ENQUETEUR':
        id_personne = _enqueteur_id_personne(request, ctx)
        if not id_personne:
            return JsonResponse({'status': 'ok', 'data': []})

    try:
        rows = db.get_suivi_aeroport(
            date_vacation,
            user_login=ctx['user_login'],
            id_societe_terrain=ctx['id_societe_terrain'],
            id_aeroport=id_aeroport,
            id_type_vol=id_type_vol,
            id_personne=id_personne,
        )
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_suivi_hors_aeroport(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_site       = int(v) if (v := request.GET.get('id_site') or None) else None
    id_personne   = int(v) if (v := request.GET.get('id_personne') or None) else None

    if ctx['role'] == 'ENQUETEUR':
        id_personne = _enqueteur_id_personne(request, ctx)
        if not id_personne:
            return JsonResponse({'status': 'ok', 'data': []})

    try:
        rows = db.get_suivi_hors_aeroport(
            date_vacation,
            user_login=ctx['user_login'],
            id_site=id_site,
            id_personne=id_personne,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_detail_vacation_hors_aeroport(request):
    ctx         = _session_ctx(request)
    id_vacation = request.GET.get('id_vacation')
    if not id_vacation:
        return JsonResponse({'status': 'error', 'message': 'id_vacation requis'}, status=400)
    try:
        rows = db.get_detail_vacation_hors_aeroport(int(id_vacation), user_login=ctx['user_login'])
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return _api_error(request, e)


# ---------------------------------------------------------------------------
# API AJAX – Affectation
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_vacations_affectation(request):
    # Lecture : accessible aussi aux superviseurs (droit 'affectation_voir').
    if not has_right(request.session.get('user_role', ''), 'affectation_voir'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    type_site     = request.GET.get('type_site', 'AEROPORT')
    id_aeroport   = int(v) if (v := request.GET.get('id_aeroport') or None) else None
    id_site       = int(v) if (v := request.GET.get('id_site') or None) else None
    id_personne   = int(v) if (v := request.GET.get('id_personne') or None) else None

    try:
        if type_site == 'HORS':
            rows = db.get_vacations_affectation_hors_aeroport(
                date_vacation,
                id_site=id_site,
                id_personne=id_personne,
                id_societe_terrain=ctx['id_societe_terrain'],
            )
        else:
            rows = db.get_vacations_affectation(
                date_vacation,
                id_aeroport=id_aeroport,
                id_personne=id_personne,
                id_societe_terrain=ctx['id_societe_terrain'],
            )
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_tous_enqueteurs(request):
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    try:
        data = db.get_tous_enqueteurs(
            date_vacation=date_vacation,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_enqueteurs_pour_affectation(request):
    """
    Candidats enquêteurs pour un emplacement de vacation précis.
    type=ZONE  → vacation zone  (id_vacation = ID_Vacation_Zone)
    sinon      → vacation aéroport (id_vacation = ID_Vacation_Enqueteur)
    Les deux espaces d'identifiants sont distincts : le type est obligatoire
    pour interroger la bonne source.
    """
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    id_vacation = request.GET.get('id_vacation')
    if not id_vacation:
        return JsonResponse({'status': 'error', 'message': 'id_vacation requis'}, status=400)
    try:
        if request.GET.get('type') == 'ZONE':
            data = db.get_enqueteurs_pour_affectation_zone(int(id_vacation))
        else:
            data = db.get_enqueteurs_pour_affectation(int(id_vacation))
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_POST
def api_set_affectation(request):
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    try:
        body          = json.loads(request.body)
        id_vacation   = int(body['id_vacation'])
        id_personne   = body.get('id_personne')
        type_vacation = body.get('type', 'AEROPORT')
        if id_personne is not None:
            id_personne = int(id_personne)
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    if type_vacation == 'ZONE':
        ok, msg = db.set_affectation_hors_aeroport(id_vacation, id_personne)
        if ok:
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error', 'message': msg or "Erreur lors de l'affectation"}, status=500)
    else:
        ok = db.set_affectation(id_vacation, id_personne)
        if ok:
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error', 'message': "Erreur lors de l'affectation"}, status=500)


# ---------------------------------------------------------------------------
# API AJAX – Commentaires
# ---------------------------------------------------------------------------

@login_required
@require_POST
def api_update_commentaire(request):
    if not has_right(request.session.get('user_role', ''), 'commentaires'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    try:
        body              = json.loads(request.body)
        id_vacation        = int(body['id_vacation'])
        commentaire_vac_1  = body.get('commentaire_vac_1') or None
        commentaire_vol_1  = body.get('commentaire_vol_1') or None
        commentaire_vac_2  = body.get('commentaire_vac_2') or None
        commentaire_vol_2  = body.get('commentaire_vol_2') or None
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    ok = db.update_commentaire(
        id_vacation,
        commentaire_vac_1,
        commentaire_vol_1,
        commentaire_vac_2,
        commentaire_vol_2,
        matricule_connexion=request.session.get('user_matricule'),
    )
    if ok:
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Erreur lors de la mise à jour'}, status=500)


@login_required
@require_POST
def api_update_commentaire_zone(request):
    """Commentaires zone (vacation + site) — depuis le détail des sites d'une zone."""
    if not has_right(request.session.get('user_role', ''), 'commentaires'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    try:
        body  = json.loads(request.body)
        id_vzs = int(body['id_vacation_zone_site'])
        vac_zone_1     = body.get('commentaire_vac_zone_1') or None
        vac_zonesite_1 = body.get('commentaire_vac_zonesite_1') or None
        vac_zone_2     = body.get('commentaire_vac_zone_2') or None
        vac_zonesite_2 = body.get('commentaire_vac_zonesite_2') or None
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    ok = db.update_commentaire_zone(
        id_vzs, vac_zone_1, vac_zonesite_1, vac_zone_2, vac_zonesite_2,
        user_login=request.session.get('user_login'),
    )
    if ok:
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Erreur lors de la mise à jour'}, status=500)


# ---------------------------------------------------------------------------
# Vérification autorisation affectation (mot de passe)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def api_check_affectation_password(request):
    try:
        body     = json.loads(request.body)
        password = body.get('password', '')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Requête invalide'}, status=400)

    if password == settings.ADMIN_PASSWORD:
        request.session['affectation_authorized'] = True
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': 'Mot de passe incorrect'}, status=403)


# ---------------------------------------------------------------------------
# API AJAX – v1.1 : Enquêteurs Solutions Terrain (§7.2)
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_enqueteurs_terrain(request):
    if not has_right(request.session.get('user_role', ''), 'enqueteurs'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)
    try:
        data = db.get_enqueteurs_terrain()
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_POST
def api_enqueteur_terrain_create(request):
    """
    Création d'un enquêteur Solutions Terrain (specs §7.2.5).
    Prc_Enqueteur_Terrain_Non_IFOP_Upsert livrée par Philippe le 25/08.
    """
    if not has_right(request.session.get('user_role', ''), 'enqueteurs'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    try:
        body   = json.loads(request.body)
        nom    = (body.get('nom') or '').strip()
        prenom = (body.get('prenom') or '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    if not nom or not prenom:
        return JsonResponse({'status': 'error', 'message': 'Informations manquantes : le nom et le prénom sont obligatoires.'}, status=400)

    ok, message = db.create_enqueteur_terrain(id_societe_terrain=2, nom=nom, prenom=prenom)
    if ok:
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': message}, status=400)



VOXCO_ECRITURE_ACTIVE = True


@login_required
@require_POST
def api_enqueteur_terrain_voxco(request):
    """
    Coche / décoche la case Voxco d'un enquêteur (specs §7.2.4 point 7).
    Même droit que la création d'enquêteur.

    Interrupteur VOXCO_ECRITURE_ACTIVE : coupé le 08/10/2026 le temps que Philippe
    corrige la procédure (elle modifiait tous les enquêteurs).
    """
    if not has_right(request.session.get('user_role', ''), 'enqueteurs'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)
    if not VOXCO_ECRITURE_ACTIVE:
        return JsonResponse({'status': 'error',
                             'message': 'La modification de la case Voxco est temporairement désactivée.'},
                            status=503)

    try:
        body = json.loads(request.body)
        id_enqueteur = int(body['id_enqueteur'])
        actif        = bool(body['actif'])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    ok, message = db.set_voxco_enqueteur_terrain(id_enqueteur, actif)
    if ok:
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': message}, status=400)


# ---------------------------------------------------------------------------
# API AJAX – v1.1 : Vacations Zone (§7.3)
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_zones_enquete(request):
    try:
        data = db.get_zones_enquete()
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_vacations_zone(request):
    if not has_right(request.session.get('user_role', ''), 'vacations_zone'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx          = _session_ctx(request)
    date_debut   = request.GET.get('date_debut', date.today().isoformat())
    date_fin     = request.GET.get('date_fin', date_debut)
    id_zone      = int(v) if (v := request.GET.get('id_zone_enquete') or None) else None
    id_enqueteur = int(v) if (v := request.GET.get('id_enqueteur') or None) else None

    try:
        data = db.get_vacations_zone(
            date_debut, date_fin,
            id_zone_enquete=id_zone,
            id_enqueteur=id_enqueteur,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_GET
def api_vacations_zone_detail(request):
    """Détail des sites d'une vacation zone — réutilise la TVF du suivi (§7.3.2 règle 03)."""
    if not has_right(request.session.get('user_role', ''), 'vacations_zone'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx         = _session_ctx(request)
    id_vacation = request.GET.get('id_vacation')
    if not id_vacation:
        return JsonResponse({'status': 'error', 'message': 'id_vacation requis'}, status=400)
    try:
        rows = db.get_detail_vacation_hors_aeroport(int(id_vacation), user_login=ctx['user_login'])
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return _api_error(request, e)


@login_required
@require_POST
def api_vacations_zone_create(request):
    if not has_right(request.session.get('user_role', ''), 'vacations_zone'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx = _session_ctx(request)
    try:
        body   = json.loads(request.body)
        lignes = body.get('lignes') or []
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    if not lignes:
        return JsonResponse({'status': 'error', 'message': 'Aucune ligne à créer.'}, status=400)

    today_iso = date.today().isoformat()
    for l in lignes:
        if not l.get('date_vacation') or not l.get('id_zone_enquete'):
            return JsonResponse({'status': 'error', 'message': 'Informations manquantes : Date et Zone sont obligatoires pour chaque ligne.'}, status=400)
        if l['date_vacation'] <= today_iso:
            return JsonResponse({'status': 'error', 'message': 'Les dates des vacations doivent être supérieures à la date du jour.'}, status=400)
        if int(l.get('nombre_enqueteurs', 1)) not in (1, 2):
            return JsonResponse({'status': 'error', 'message': 'Le nombre d\'enquêteurs doit être 1 ou 2.'}, status=400)

    ok, message = db.create_vacations_zone(ctx['id_societe_terrain'], lignes)
    if ok:
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': message}, status=400)
