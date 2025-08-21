from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from Departement.models import KPI, KPISubmission
from SMQ.models import RapportKPI
from datetime import date
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import JsonResponse
from Departement.models import KPISubmission


def page_tableau_bord(request):
    # Récupérer la liste des départements depuis le modèle
    departements = KPI.DEPARTEMENTS

    # Récupérer le filtre département depuis GET (ou None si absent)
    filtre_departement = request.GET.get("departement")
    if not filtre_departement :
        filtre_departement = 'Ressources humaines'

    # --- Calcul des KPI Cards (valeurs statiques) ---
    today = date.today()
    this_month_start = today.replace(day=1)

    # KPI 1: KPIs reçus (soumis) ce mois
    kpis_recus_count = KPISubmission.objects.filter(
        date_soumission__gte=this_month_start
    ).count()

    for _ in KPISubmission.objects.all() :
          print(_)

    # KPI 2: Rapports générés ce mois
    rapports_generes_count = RapportKPI.objects.filter(
        generated_at__gte=this_month_start
    ).count()

    # KPI 3: Taux de validation des KPI (validés / total)
    total_kpis_submissions = KPISubmission.objects.count()
    validated_kpis_submissions = KPISubmission.objects.filter(etat="Validée").count()
    taux_validation = (
        (validated_kpis_submissions / total_kpis_submissions) * 100
        if total_kpis_submissions > 0
        else 0
    )

    # --- Préparation des données pour les graphiques ---
    kpi_chart_data = {}

    # On parcourt tous les KPI, filtrés si un département est choisi
    kpis_to_chart = KPI.objects.all()
    if filtre_departement and filtre_departement != "all":
        kpis_to_chart = kpis_to_chart.filter(departement=filtre_departement)

    for kpi in kpis_to_chart:
        # On récupère toutes les soumissions pour ce KPI, triées
        soumissions = kpi.soumissions.order_by("periode_annee", "periode_mois")

        labels, values = [], []
        for s in soumissions:
            if s.periode_mois == 0:
                label = f"{s.periode_annee}"
            else:
                label = f"{s.periode_mois}/{s.periode_annee}"
            labels.append(label)
            
            try:
                # La valeur peut être une chaîne de caractères, on la convertit en float
                val = float(s.valeur)
                values.append(val)
            except (ValueError, TypeError):
                # Si la conversion échoue, on met 0 ou une valeur par défaut
                values.append(0)

        # On détermine si c’est un KPI exprimé en pourcentage
        is_percent = "%" in (kpi.valeur_cible or "")

        # On ajoute les données dans le dict avec le nom du KPI
        kpi_chart_data[kpi.nom] = {
            "labels": labels,
            "values": values,
            "is_percent": bool(is_percent),  # converti explicitement en True/False
        }


    # Données pour le graphique "Rapports générés"
    rapports_par_mois = (
        RapportKPI.objects.annotate(
            month=ExtractMonth("generated_at"), year=ExtractYear("generated_at")
        )
        .values("year", "month")
        .annotate(count=Count("id"))
        .order_by("year", "month")
    )
    
    report_labels = []
    report_values = []
    for r in rapports_par_mois:
        report_labels.append(f"{r['month']}/{r['year']}")
        report_values.append(r['count'])

    context = {
        "pagename": "tableau-bord",
        "departements": list(departements),
        "filtre_departement": filtre_departement,
        "kpis_recus_count": kpis_recus_count,
        "rapports_generes_count": rapports_generes_count,
        "taux_validation": round(taux_validation, 2),  # Arrondir le taux
        "kpi_chart_data": kpi_chart_data,
        "report_chart_data": {
            "labels": report_labels,
            "values": report_values,
        },
    }

    return render(request, "smq/tableau_bord.html", context=context)


def soumissions_en_attente(request):
    soumissions = KPISubmission.objects.filter(etat="En attente").select_related("kpi", "soumis_par")[:50]
    data = []

    for s in soumissions:
        data.append({
            "kpi": s.kpi.nom,
            "valeur": s.valeur,
            "periode_mois": s.periode_mois,
            "periode_annee": s.periode_annee,
            "soumis_par": s.soumis_par.get_full_name() if s.soumis_par else "Utilisateur supprimé",
            "observation": s.observation,
            "departement": s.kpi.departement,
        })

    return JsonResponse({"soumissions": data})

