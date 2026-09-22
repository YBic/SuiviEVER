"""Décorateurs utilitaires pour les vues (auth, droits)."""
from functools import wraps
from django.shortcuts import redirect
from accounts.roles import has_right


def _is_ajax(request) -> bool:
    """True si la requête est un appel AJAX (jQuery ou fetch avec header standard)."""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


def login_required(view_func):
    """
    Redirige vers /login/ si l'utilisateur n'est pas connecté.
    Pour les appels AJAX, renvoie un 401 JSON (pas de redirect)
    afin que le JS puisse rediriger proprement vers /login/.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_login'):
            if _is_ajax(request):
                from django.http import JsonResponse
                return JsonResponse({'status': 'error', 'code': 'session_expired'}, status=401)
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_right(feature):
    """Redirige vers /login/ si le rôle de l'utilisateur n'a pas accès à la fonctionnalité."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('user_login'):
                if _is_ajax(request):
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'code': 'session_expired'}, status=401)
                return redirect('accounts:login')
            role = request.session.get('user_role', '')
            if not has_right(role, feature):
                return redirect('core:suivi_aeroport')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
