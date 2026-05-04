"""
Vues principales de l'application EVER.
Architecture AJAX-driven : les pages rendent le squelette HTML,
les données sont chargées dynamiquement via les endpoints /api/*.
"""
import json
from datetime import date

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings

from .decorators import login_required, require_right
from accounts.roles import has_right
from . import db


# ---------------------------------------------------------------------------
# Helpers de session
# ---------------------------------------------------------------------------

def _session_ctx(request) -> dict:
    """
    Retourne les valeurs de session fréquemment utilisées dans les vues API.
    Centralise l'extraction pour éviter la répétition.
    """
    return {
        'role':              request.session.get('user_role', 'ENQUETEUR'),
        'user_id':           request.session.get('user_id'),
        'user_login':        request.session.get('user_login'),
        'matricule':         request.session.get('user_matricule'),
        'id_societe_terrain': request.session.get('user_id_societe_terrain'),
    }


# ---------------------------------------------------------------------------
# Pages principales
# ---------------------------------------------------------------------------

@login_required
def suivi_aeroport(request):
    """Page de suivi des vacations en aéroport."""
    role = request.session.get('user_role', '')
    context = {
        'page':                 'suivi_aeroport',
        'can_filter_enqueteur': has_right(role, 'filtrer_enqueteur'),
        'can_comment':          has_right(role, 'commentaires'),
        'can_affectation':      has_right(role, 'affectation'),
        'today':                date.today(),
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
        'can_affectation':      has_right(role, 'affectation'),
        'today':                date.today(),
    }
    return render(request, 'core/suivi_hors_aeroport.html', context)


@require_right('affectation')
def affectation(request):
    """Page d'affectation des enquêteurs aux vacations."""
    context = {
        'page':           'affectation',
        'today':          date.today(),
        'can_affectation': True,   # toujours True ici : le décorateur filtre déjà l'accès
    }
    return render(request, 'core/affectation.html', context)


# ---------------------------------------------------------------------------
# API AJAX – Listes de référence
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_periodes(request):
    try:
        data = db.get_periodes()
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def api_sites(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_personne   = ctx['user_id'] if ctx['role'] == 'ENQUETEUR' else None
    try:
        data = db.get_sites(
            date_vacation,
            id_societe_terrain=ctx['id_societe_terrain'],
            id_personne=id_personne,
        )
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ---------------------------------------------------------------------------
# API AJAX – Données de suivi
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_suivi_aeroport(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_aeroport   = request.GET.get('id_aeroport') or None
    id_personne   = request.GET.get('id_personne') or None
    id_type_vol   = request.GET.get('id_type_vol') or None

    # Un enquêteur ne voit que ses propres vacations
    if ctx['role'] == 'ENQUETEUR':
        id_personne = ctx['user_id']

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
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def api_suivi_hors_aeroport(request):
    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_site       = request.GET.get('id_site') or None
    id_personne   = request.GET.get('id_personne') or None

    if ctx['role'] == 'ENQUETEUR':
        id_personne = ctx['user_id']

    try:
        rows = db.get_suivi_hors_aeroport(
            date_vacation,
            id_site=id_site,
            id_personne=id_personne,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def api_detail_vacation_hors_aeroport(request):
    id_vacation = request.GET.get('id_vacation')
    if not id_vacation:
        return JsonResponse({'status': 'error', 'message': 'id_vacation requis'}, status=400)
    try:
        rows = db.get_detail_vacation_hors_aeroport(int(id_vacation))
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ---------------------------------------------------------------------------
# API AJAX – Affectation
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_vacations_affectation(request):
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx           = _session_ctx(request)
    date_vacation = request.GET.get('date', date.today().isoformat())
    id_aeroport   = request.GET.get('id_aeroport') or None
    id_personne   = request.GET.get('id_personne') or None

    try:
        rows = db.get_vacations_affectation(
            date_vacation,
            id_aeroport=id_aeroport,
            id_personne=id_personne,
            id_societe_terrain=ctx['id_societe_terrain'],
        )
        return JsonResponse({'status': 'ok', 'data': rows})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def api_tous_enqueteurs(request):
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    ctx = _session_ctx(request)
    try:
        data = db.get_tous_enqueteurs(id_societe_terrain=ctx['id_societe_terrain'])
        return JsonResponse({'status': 'ok', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def api_set_affectation(request):
    if not has_right(request.session.get('user_role', ''), 'affectation'):
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'}, status=403)

    try:
        body        = json.loads(request.body)
        id_vacation = int(body['id_vacation'])
        id_personne = body.get('id_personne')
        if id_personne is not None:
            id_personne = int(id_personne)
        # rang prévu par le CdC (ft_EVER_Set_Affectation) mais absent de la SP actuelle
        # conservé dans le body pour ne pas casser le JS quand Philippe livrera la nouvelle SP
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

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
        id_vacation       = int(body['id_vacation'])
        commentaire_avant = body.get('commentaire_avant') or None
        commentaire_apres = body.get('commentaire_apres') or None
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Paramètres invalides'}, status=400)

    ok = db.update_commentaire(
        id_vacation,
        commentaire_avant,
        commentaire_apres,
        matricule_connexion=request.session.get('user_matricule'),
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
