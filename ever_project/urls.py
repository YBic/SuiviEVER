from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='core:suivi_aeroport', permanent=False)),
    path('', include('accounts.urls')),
    path('', include('core.urls')),
]
