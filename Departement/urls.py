from django.urls import path
from .views import page_tableau_bord
from .views import soumissions_dispatch


app_name = "departement"


urlpatterns = [
    path('<slug:departement_slug>/tableau-bord/', page_tableau_bord, name="departement_tableau_bord"),
    path('<slug:departement_slug>/soumissions/', soumissions_dispatch, name="departement_soumissions"),
]

