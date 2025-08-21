import datetime
from pathlib import Path
import sqlite3
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib import messages
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import translation
from django.utils.formats import date_format
from .models import KPI, KPISubmission
from .kpi_calculators import calculer_valeur_kpi


def calculate_kpi_value_from_file(fichier):
    # TODO: Implémenter la logique d'extraction depuis fichier Excel ou CSV
    return 0


def get_kpi_factors(kpi, periode_annee, periode_mois):
    """
    Récupère les facteurs nécessaires pour le calcul du KPI depuis la base externe.
    Ajoute les valeurs complémentaires comme taux_turnover et taux_restant si applicable.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "external_data.sqlite"
    factors = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if kpi.nom == "Turnover/ Taux de roulement du personnel":
            # Nombre départs

            if periode_mois:
                cur.execute("""
                    SELECT COUNT(*) FROM Depart
                    WHERE strftime('%Y', date_depart) = ? AND strftime('%m', date_depart) = ?
                """, (str(periode_annee), f"{periode_mois:02d}"))
            else:
                cur.execute("""
                    SELECT COUNT(*) FROM Depart
                    WHERE strftime('%Y', date_depart) = ?
                """, (str(periode_annee),))
            nbre_depart = cur.fetchone()[0]

            # Effectif total
            cur.execute("""
                SELECT COUNT(*) FROM Agent
                WHERE CAST(strftime('%Y', date_entree) AS INTEGER) <= ?
            """, (periode_annee,))
            effectif_total = cur.fetchone()[0]

            # Calcul des taux
            taux_turnover = (nbre_depart / effectif_total * 100) if effectif_total else 0
            taux_restant = 100 - taux_turnover


            factors = {
                "nbre_depart": nbre_depart,
                "effectif_total": effectif_total,
                "taux_turnover": round(taux_turnover, 2),
                "taux_restant": round(taux_restant, 2),
            }

        conn.close()
    except Exception as e:
        print(f"Erreur récupération facteurs base externe : {e}")

    return factors


def extract_value_from_base(kpi, periode_annee, periode_mois):
    """
    Calcule la valeur du KPI à partir des facteurs extraits depuis la base externe.
    """
    factors = get_kpi_factors(kpi, periode_annee, periode_mois)
    
    if not factors or factors.get("effectif_total", 0) == 0:
        return None
    return calculer_valeur_kpi(kpi, periode_annee, periode_mois, **factors)

import datetime
import re
from pathlib import Path
import sqlite3
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib import messages
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import translation
from django.utils.formats import date_format
from .models import KPI, KPISubmission
from .kpi_calculators import calculer_valeur_kpi

def is_kpi_conform(valeur_soumise, cible_str):
    """
    Vérifie si la valeur soumise est conforme à la cible.
    Gère les opérateurs de comparaison : ≤, ≥, <, >, =.
    """
    if not valeur_soumise or not cible_str:
        return None

    try:
        valeur_num = float(valeur_soumise)
    except (ValueError, TypeError):
        return None

    # Extraction de l'opérateur et de la valeur numérique de la cible
    match = re.match(r'([≤≥<>])?\s*([0-9.]+)', cible_str.replace(',', '.').strip())
    if not match:
        # Gérer les cibles sans opérateur explicite (égalité implicite)
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
    
    return None

def calculate_kpi_value_from_file(fichier):
    # TODO: Implémenter la logique d'extraction depuis fichier Excel ou CSV
    return 0

def get_kpi_factors(kpi, periode_annee, periode_mois):
    """
    Récupère les facteurs nécessaires pour le calcul du KPI depuis la base externe.
    Ajoute les valeurs complémentaires comme taux_turnover et taux_restant si applicable.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "external_data.sqlite"
    factors = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if kpi.nom == "Turnover/ Taux de roulement du personnel":
            # Nombre départs
            if periode_mois:
                cur.execute("""
                    SELECT COUNT(*) FROM Depart
                    WHERE strftime('%Y', date_depart) = ? AND strftime('%m', date_depart) = ?
                """, (str(periode_annee), f"{periode_mois:02d}"))
            else:
                cur.execute("""
                    SELECT COUNT(*) FROM Depart
                    WHERE strftime('%Y', date_depart) = ?
                """, (str(periode_annee),))
            nbre_depart = cur.fetchone()[0]
            # Effectif total
            cur.execute("""
                SELECT COUNT(*) FROM Agent
                WHERE CAST(strftime('%Y', date_entree) AS INTEGER) <= ?
            """, (periode_annee,))
            effectif_total = cur.fetchone()[0]
            # Calcul des taux
            taux_turnover = (nbre_depart / effectif_total * 100) if effectif_total else 0
            taux_restant = 100 - taux_turnover
            factors = {
                "nbre_depart": nbre_depart,
                "effectif_total": effectif_total,
                "taux_turnover": round(taux_turnover, 2),
                "taux_restant": round(taux_restant, 2),
            }
        conn.close()
    except Exception as e:
        print(f"Erreur récupération facteurs base externe : {e}")
    return factors

def extract_value_from_base(kpi, periode_annee, periode_mois):
    """
    Calcule la valeur du KPI à partir des facteurs extraits depuis la base externe.
    """
    factors = get_kpi_factors(kpi, periode_annee, periode_mois)
    
    if not factors or factors.get("effectif_total", 0) == 0:
        return None
    return calculer_valeur_kpi(kpi, periode_annee, periode_mois, **factors)


def soumissions_rh(request, departement_slug):
    default_year = datetime.date.today().year
    default_month = datetime.date.today().month
    default_dept = "Ressources humaines"
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

    # Récupération des KPI pour le département sélectionné
    kpis = KPI.objects.filter(departement=selected_dept).order_by("nom")
    kpis_with_targets = [
        (kpi, kpi.valeur_cible, getattr(kpi, 'source_type', 'manuel')) 
        for kpi in kpis
    ]

    # Récupération des dernières soumissions par KPI, période et utilisateur
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
        # Déterminer la conformité de la soumission
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
        
        if existing:
            submission.source_type = source
            submission.etat = "En attente"

        submission.observation = observation

        if source == "fichier":
            if not fichier:
                messages.error(request, "Fichier requis pour ce type de source.")
                return redirect(request.META.get("HTTP_REFERer", request.path))
            
            valeur_extraite = calculate_kpi_value_from_file(fichier)
            if valeur_extraite is None:
                messages.error(request, "Impossible d'extraire la valeur du fichier Excel.")
                return redirect(request.META.get("HTTP_REFERer", request.path))
            submission.valeur = valeur_extraite
        elif source == "manuel":
            if not valeur:
                messages.error(request, "Valeur requise pour saisie manuelle.")
                return redirect(request.META.get("HTTP_REFERer", request.path))
            submission.valeur = valeur
        elif source == "base":
            factors = get_kpi_factors(kpi, periode_annee, periode_mois)
            valeur_extraite = extract_value_from_base(kpi, periode_annee, periode_mois)
            if valeur_extraite is None:
                messages.error(request, "Impossible d'extraire la valeur depuis la source automatique.")
                return redirect(request.META.get("HTTP_REFERer", request.path))
            submission.valeur = valeur_extraite
            submission.facteurs_utilises = factors
        else:
            messages.error(request, "Type de source inconnu.")
            return redirect(request.META.get("HTTP_REFERer", request.path))

        submission.save()
        messages.success(request, f"Soumission du KPI « {kpi.nom} » enregistrée pour {selected_dept}.")
        url = reverse("departement:departement_soumissions", kwargs={"departement_slug": departement_slug})
        query_string = urlencode({
            "annee": periode_annee,
            "mois": periode_mois,
            "departement": selected_dept,
        })
        return redirect(f"{url}?{query_string}")

    # Préparation des mois pour le template
    with translation.override('fr'):
        mois_dict = {i: date_format(datetime.date(1900, i, 1), 'F') for i in range(1, 13)}

    context = {
        "kpis_with_targets": kpis_with_targets,
        "latest_submissions": latest_submissions,
        "year": selected_year_int,
        "month": selected_month_int,
        "years": [default_year - i for i in range(4)],
        "months": list(mois_dict.items()),
        "pagename": "soumissions_kpi_rh",
        "departement_slug": departement_slug,
        "departement": selected_dept,
    }
    return render(request, "departement/rh/soumissions.html", context)
