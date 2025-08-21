from django.urls import path
from .views import (
    page_tableau_bord,
    soumissions_en_attente,
)
from .views_kpi import (
    update_kpi_target,
    changer_etat_kpi,
    page_kpi,
)
from .views_utilisateurs import (
    utilisateurs,
    add_utilisateurs,
    edit_utilisateurs,
    delete_utilisateurs,
)
from .views_rapport_kpi import (
    rapports_kpi,
    delete_rapport_kpi,
    generate_rapport_kpi,
    view_pdf,
)


urlpatterns = [

    # Vues pour les rapports KPIs
    path("rapports-kpi/", rapports_kpi, name="smq/rapports-kpi"),
    path("rapports-kpi/delete/<int:pk>/", delete_rapport_kpi, name="smq/delete-rapport-kpi"),
    path("rapports-kpi/generate/", generate_rapport_kpi, name="smq/generate-rapport-kpi"),
    path('media/rapports_kpi/<str:filename>/', view_pdf, name='view-pdf'),

    # Vue pour le tableau de bord
    path("tableau-bord/", page_tableau_bord, name="smq/tableau-bord"),

    # Vues pour les KPIs
    path("kpi/", page_kpi, name="smq/kpi"),
    path("kpi/update-target/", update_kpi_target, name="update_kpi_target"),
    path("changer-etat-kpi/", changer_etat_kpi, name="changer_etat_kpi"),

    # Vues utilisateurs
    path('utilisateurs/', utilisateurs, name='smq/utilisateurs'),
    path('utilisateurs/add/', add_utilisateurs, name='smq/add-utilisateurs'),
    path('utilisateurs/edit/', edit_utilisateurs, name='smq/edit-utilisateurs'),
    path('utilisateurs/delete/<int:user_id>/', delete_utilisateurs, name='smq/delete-utilisateurs'),

    path('soumissions-en-attente/', soumissions_en_attente, name='soumissions_en_attente'),

]

