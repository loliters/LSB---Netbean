from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),

    path('panel/estudiante/', views.panel_estudiante, name='panel_estudiante'),
    path('panel/profesor/', views.panel_profesor, name='panel_profesor'),
    path('panel/admin/', views.panel_admin, name='panel_admin'),
]