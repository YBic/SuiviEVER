"""Décorateurs utilitaires pour les vues (auth, droits)."""
from functools import wraps
from django.shortcuts import redirect
from accounts.roles import has_right


def login_required(view_func):
    """Redirige vers /login/ si l'utilisateur n'est pas connecté."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_login'):
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_right(feature):
    """Redirige vers /login/ si le rôle de l'utilisateur n'a pas accès à la fonctionnalité."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('user_login'):
                return redirect('accounts:login')
            role = request.session.get('user_role', '')
            if not has_right(role, feature):
                return redirect('core:suivi_aeroport')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
