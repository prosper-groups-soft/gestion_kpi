import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib import messages
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from .models import KPI, KPISubmission
from django.utils import translation
from django.utils.formats import date_format
from pathlib import Path
import pandas as pd
import re
from .kpi_calculators import calculer_valeur_kpi


def is_kpi_conform(valeur_soumise, cible_str):
    """
    Vérifie si la valeur soumise est conforme à la cible.
    Gère les opérateurs de comparaison : ≤, ≥, <, >, =.
    """
    if valeur_soumise is None or cible_str is None:
        return None

    try:
        valeur_num = float(valeur_soumise)
    except (ValueError, TypeError):
        return None

    match = re.match(r'([≤≥<>])?\s*([0-9.]+)', cible_str.replace(',', '.').strip())
    if not match:
        try:
            cible_num = float(cible_str.replace(',', '.').strip())
            return valeur_num == cible_num
        except (ValueError, TypeError):
            return None

    op = match.group(1) if match.group(1) else '='
    cible_num = float(match.group(2))

    if op == '≤':
        return valeur_num <= cible_num
    elif op == '≥':
        return valeur_num >= cible_num
    elif op == '<':
        return valeur_num < cible_num
    elif op == '>':
        return valeur_num > cible_num
    elif op == '=':
        return valeur_num == cible_num
    

def calculate_kpi_value_from_file(fichier):
    """
    Calcule le KPI 'Taux de fidélisation des clients Garage' à partir du fichier Excel.
    Retourne la valeur calculée et les facteurs utilisés.
    """
    try:
        # Lire le fichier Excel
        df = pd.read_excel(fichier)
        df = df.dropna(subset=["EstRevenuPourEntretien", "EstPrévuProchainEntretien"])

        # Comptages
        nbre_clients_revenus = df[df["EstRevenuPourEntretien"].str.lower() == "oui"].shape[0]
        nbre_clients_prevu = df[df["EstPrévuProchainEntretien"].str.lower() == "oui"].shape[0]

        # Récupérer le KPI dans la base
        from .models import KPI
        kpi = KPI.objects.get(nom="Taux de fidélisation des clients Garage")

        # Calcul via le système de calculateurs
        taux_fidelisation = calculer_valeur_kpi(
            kpi,
            periode_annee=None,
            periode_mois=None,
            df_clients=df  # passer le dataframe complet
        )

        # Protection pour ne pas dépasser 100%
        taux_fidelisation = min(max(taux_fidelisation, 0), 100)
        taux_non_fidelisation = round(100 - taux_fidelisation, 2)

        facteurs = {
            "nbre_clients_revenus": nbre_clients_revenus,
            "nbre_clients_prevu": nbre_clients_prevu,
            "taux_fidelisation": taux_fidelisation,
            "taux_non_fidelisation": taux_non_fidelisation,
        }

        return taux_fidelisation, facteurs

    except Exception as e:
        print("Erreur extraction KPI Garage:", e)
        return None, {}


def extract_value_from_base(kpi, periode_annee, periode_mois, request):
    """
    Pour Garage, pas d'extraction automatique depuis base externe.
    """
    return None, {}


def soumissions_garage(request, departement_slug):
    default_year = datetime.date.today().year
    default_month = datetime.date.today().month
    default_dept = "Garage"

    selected_year = request.GET.get("annee")
    selected_month = request.GET.get("mois")
    selected_dept = request.GET.get("departement", default_dept)

    need_redirect = False
    params = {}

    # Validation année
    try:
        selected_year_int = int(selected_year)
    except (TypeError, ValueError):
        selected_year_int = default_year
        need_redirect = True
    params["annee"] = str(selected_year_int)

    # Validation mois
    try:
        selected_month_int = int(selected_month)
        if not (1 <= selected_month_int <= 12):
            raise ValueError()
    except (TypeError, ValueError):
        selected_month_int = default_month
        need_redirect = True
    params["mois"] = str(selected_month_int)

    # Validation département
    if not selected_dept:
        selected_dept = default_dept
        need_redirect = True
    params["departement"] = selected_dept

    if need_redirect:
        url = reverse("departement:departement_soumissions", kwargs={"departement_slug": departement_slug})
        url += "?" + urlencode(params)
        return redirect(url)

    # Filtrer KPI pour Garage uniquement
    kpis = KPI.objects.filter(departement=selected_dept).order_by("nom")
    kpis_with_targets = [(kpi, kpi.valeur_cible, getattr(kpi, 'source_type', 'manuel')) for kpi in kpis]

    # Pour Garage, valeurs extraites initialement None
    values_extracted = {kpi.id: None for kpi in kpis}

    submissions_qs = KPISubmission.objects.filter(
        kpi__departement=selected_dept,
        periode_annee=selected_year_int,
        periode_mois=selected_month_int,
    )
    latest_submissions_qs = submissions_qs.annotate(
        rn=Window(
            expression=RowNumber(),
            partition_by=[F("kpi_id")],
            order_by=F("date_soumission").desc()
        )
    ).filter(rn=1)
    latest_submissions = {}

    for sub in latest_submissions_qs:
        kpi = get_object_or_404(KPI, pk=sub.kpi_id)
        # Déterminer si la soumission est conforme à la cible
        sub.is_conform = is_kpi_conform(sub.valeur, kpi.valeur_cible)
        latest_submissions[sub.kpi_id] = sub

    if request.method == "POST":
        kpi_id = request.POST.get("kpi_id")
        source = request.POST.get("source_type")
        valeur = request.POST.get("valeur", "").strip()
        observation = request.POST.get("observation", "").strip()
        fichier = request.FILES.get("fichier")
        
        try:
            periode_annee = int(request.POST.get("periode_annee"))
        except (TypeError, ValueError):
            messages.error(request, "Année de période invalide.")
            return redirect(request.META.get("HTTP_REFERER", request.path))

        periode_mois_raw = request.POST.get("periode_mois") or None
        periode_mois = None
        if periode_mois_raw:
            try:
                periode_mois = int(periode_mois_raw)
            except ValueError:
                messages.error(request, "Mois de période invalide.")
                return redirect(request.META.get("HTTP_REFERER", request.path))

        kpi = get_object_or_404(KPI, pk=kpi_id, departement=selected_dept)
        user = request.user

        existing = KPISubmission.objects.filter(
            kpi=kpi,
            periode_annee=periode_annee,
            periode_mois=periode_mois,
            soumis_par=user,
        ).first()

        submission = existing or KPISubmission(
            kpi=kpi,
            periode_annee=periode_annee,
            periode_mois=periode_mois,
            source_type=source,
            soumis_par=user,
            etat="En attente",
        )

        # Mettre à jour l'état et la source si existant
        if existing:
            submission.source_type = source
            submission.etat = "En attente"

        submission.observation = observation

        # Gestion selon le type de source
        facteurs_utilises = {}
        if source == "fichier":
            if not fichier:
                messages.error(request, "Fichier requis pour ce type de source.")
                return redirect(request.META.get("HTTP_REFERER", request.path))

            valeur_extraite, facteurs_utilises = calculate_kpi_value_from_file(fichier)
            if valeur_extraite is None:
                messages.error(request, "Impossible d'extraire la valeur du fichier Excel.")
                return redirect(request.META.get("HTTP_REFERER", request.path))
            submission.valeur = valeur_extraite
            submission.facteurs_utilises = facteurs_utilises

        elif source == "manuel":
            if not valeur:
                messages.error(request, "Valeur requise pour saisie manuelle.")
                return redirect(request.META.get("HTTP_REFERER", request.path))
            submission.valeur = valeur

        elif source == "base":
            valeur_extraite, facteurs_utilises = extract_value_from_base(kpi, periode_annee, periode_mois, request)
            if valeur_extraite is None:
                messages.error(request, "Impossible d'extraire la valeur depuis la source automatique.")
                return redirect(request.META.get("HTTP_REFERER", request.path))
            submission.valeur = valeur_extraite
            submission.facteurs_utilises = facteurs_utilises

        else:
            messages.error(request, "Type de source inconnu.")
            return redirect(request.META.get("HTTP_REFERER", request.path))

        submission.save()
        messages.success(request, f"Soumission du KPI « {kpi.nom} » enregistrée pour {selected_dept}.")

        url = reverse("departement:departement_soumissions", kwargs={"departement_slug": departement_slug})
        query_string = urlencode({
            "annee": periode_annee,
            "mois": periode_mois,
            "departement": selected_dept,
        })
        return redirect(f"{url}?{query_string}")

    with translation.override('fr'):
        mois_dict = {i: date_format(datetime.date(1900, i, 1), 'F') for i in range(1, 13)}

    context = {
        "kpis_with_targets": kpis_with_targets,
        "latest_submissions": latest_submissions,
        "values_extracted": values_extracted,
        "year": selected_year_int,
        "month": selected_month_int,
        "years": [default_year - i for i in range(4)],
        "months": list(mois_dict.items()),
        "pagename": "soumissions_kpi_garage",
        "departement_slug": departement_slug,
        "departement": selected_dept,
    }

    return render(request, "departement/garage/soumissions.html", context)
