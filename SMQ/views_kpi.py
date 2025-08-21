from django.shortcuts import render, redirect, get_object_or_404
from Departement.models import KPISubmission, KPI
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import translation
from django.utils.formats import date_format
from django.urls import reverse
from django.http import HttpResponseRedirect
from urllib.parse import urlencode


def changer_etat_kpi(request):

    try:
        soum_id = int(request.POST.get("soumission_id"))
        soum = KPISubmission.objects.get(id=soum_id)

        etat = request.POST.get("etat", "").strip()
        if etat in dict(KPISubmission.ETAT_CHOICES):
            soum.etat = etat
            soum.save()
            messages.success(request, "État mis à jour.")
        else:
            messages.error(request, "État invalide.")

    except Exception as e:
        messages.error(request, f"Erreur : {e}")
    
    return redirect(request.META.get("HTTP_REFERER", "page_kpi"))


def update_kpi_target(request):
    """
    Vue pour mettre à jour la valeur cible d'un KPI.
    """
    kpi_id = request.POST.get("kpi_id")
    valeur_cible = request.POST.get("valeur_cible", "").strip()
    
    # Récupérer les paramètres de redirection pour revenir à la bonne page
    departement = request.POST.get("filtre_departement")
    annee = request.POST.get("filtre_annee")
    mois = request.POST.get("filtre_mois")

    try:
        kpi = get_object_or_404(KPI, pk=kpi_id)
        # S'assurer que seul un utilisateur autorisé peut modifier la cible
        # (à adapter selon votre logique de permissions)
        # Exemple: if not request.user.has_perm('app_name.change_kpi_target', kpi):
        #   messages.error(request, "Vous n'avez pas la permission de modifier cette cible.")
        #   return redirect(...)

        if not valeur_cible:
            messages.error(request, "La valeur cible ne peut pas être vide.")
        else:
            kpi.valeur_cible = valeur_cible
            kpi.save()
            messages.success(request, f"La cible pour le KPI '{kpi.nom}' a été mise à jour.")
            
    except KPI.DoesNotExist:
        messages.error(request, "KPI introuvable.")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la mise à jour : {e}")
    
    # Rediriger l'utilisateur vers la page de soumissions avec les bons filtres
    url = reverse("departement:departement_soumissions", kwargs={"departement_slug": departement})
    query_string = urlencode({
        "annee": annee,
        "mois": mois,
        "departement": departement,
    })
    return redirect(request.META.get("HTTP_REFERER", "page_kpi"))



def page_kpi(request):
    default_year = datetime.now().year
    default_month = datetime.now().month

    selected_year = request.GET.get("annee")
    selected_month = request.GET.get("mois")
    selected_dept = request.GET.get("departement")

    # Détection des filtres absents
    need_redirect = False
    params = {}

    # Année
    try:
        selected_year_int = int(selected_year)
    except (TypeError, ValueError):
        selected_year_int = default_year
        need_redirect = True
    params["annee"] = str(selected_year_int)

    # Mois
    try:
        selected_month_int = int(selected_month)
    except (TypeError, ValueError):
        selected_month_int = default_month
        need_redirect = True
    params["mois"] = str(selected_month_int)

    # Département
    if not selected_dept:
        selected_dept = KPI.DEPARTEMENTS[0][0] if KPI.DEPARTEMENTS else ""
        need_redirect = True
    params["departement"] = selected_dept

    if need_redirect:
        url = reverse("smq/kpi") + "?" + urlencode(params)
        return HttpResponseRedirect(url)

    # Puis le reste du traitement classique avec selected_year_int, selected_month_int, selected_dept

    # Filtrer KPIs
    kpi_filter = {"departement": selected_dept} if selected_dept else {}
    kpis = KPI.objects.filter(**kpi_filter).order_by("nom")

    # Filtrer Soumissions
    soumissions = KPISubmission.objects.select_related("kpi").filter(
        periode_annee=selected_year_int,
        periode_mois=selected_month_int,
        kpi__departement=selected_dept,
    )

    submissions_map = defaultdict(list)
    for s in soumissions:
        submissions_map[s.kpi.id].append(s)

    lignes = []
    for kpi in kpis:
        soum_list = submissions_map.get(kpi.id, [])
        soum = soum_list[0] if soum_list else None
        lignes.append({
            "kpi": kpi,
            "soumission": soum,
            "mois": selected_month_int,
            "annee": selected_year_int,
            "cible": getattr(kpi, "valeur_cible", None),
        })

    with translation.override('fr'):
        mois_dict = {i: date_format(datetime(1900, i, 1), 'F') for i in range(1, 13)}

    context = {
        "lignes": lignes,
        "filtre_annee": str(selected_year_int),
        "filtre_mois": str(selected_month_int),
        "filtre_departement": selected_dept,
        "departements": KPI.DEPARTEMENTS,
        "annees": [default_year],
        "mois": mois_dict,
        "pagename": "kpi"
    }

    return render(request, "smq/kpi.html", context)

