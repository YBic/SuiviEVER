from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',        views.login_view,        name='login'),
    path('set-password/', views.set_password_view, name='set_password'),
    path('logout/',       views.logout_view,        name='logout'),
]
