from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Pages
    path('suivi/aeroport/', views.suivi_aeroport, name='suivi_aeroport'),
    path('suivi/hors-aeroport/', views.suivi_hors_aeroport, name='suivi_hors_aeroport'),
    path('affectation/', views.affectation, name='affectation'),

    # API - listes de référence
    path('api/periodes/', views.api_periodes, name='api_periodes'),
    path('api/aeroports/', views.api_aeroports, name='api_aeroports'),
    path('api/sites/', views.api_sites, name='api_sites'),
    path('api/enqueteurs/aeroport/', views.api_enqueteurs_aeroport, name='api_enqueteurs_aeroport'),
    path('api/enqueteurs/site/', views.api_enqueteurs_site, name='api_enqueteurs_site'),

    # API - suivi
    path('api/suivi/aeroport/', views.api_suivi_aeroport, name='api_suivi_aeroport'),
    path('api/suivi/hors-aeroport/', views.api_suivi_hors_aeroport, name='api_suivi_hors_aeroport'),
    path('api/suivi/hors-aeroport/detail/', views.api_detail_vacation_hors_aeroport, name='api_detail_vacation'),

    # API - affectation
    path('api/affectation/vacations/', views.api_vacations_affectation, name='api_vacations_affectation'),
    path('api/affectation/enqueteurs/', views.api_tous_enqueteurs, name='api_tous_enqueteurs'),
    path('api/affectation/set/', views.api_set_affectation, name='api_set_affectation'),
    path('api/affectation/password/', views.api_check_affectation_password, name='api_affectation_password'),

    # API - commentaires
    path('api/commentaire/', views.api_update_commentaire, name='api_commentaire'),
]
