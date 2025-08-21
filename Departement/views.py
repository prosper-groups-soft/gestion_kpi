from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.timezone import now
from .models import KPISubmission
from django.http import Http404
from django.utils.text import slugify
from .views_rh import soumissions_rh
from .views_garage import soumissions_garage
from django.db.models import Count, Q
from django.utils.text import slugify
from collections import defaultdict


DEPARTEMENTS = [
    ("Ressources humaines", "Ressources humaines"),
    ("Garage", "Garage"),
]


# Mapping slug -> nom département (réutilise DEPARTEMENTS défini ailleurs)
DEPT_SLUG_TO_NAME = {}
for dept_name, _ in DEPARTEMENTS:
    # utilise django.slugify pour uniformiser
    s = slugify(dept_name).lower()
    DEPT_SLUG_TO_NAME[s] = dept_name
    # aussi la version sans tirets pour tolérance (ex: "relationsclients")
    DEPT_SLUG_TO_NAME[s.replace("-", "")] = dept_name


# mapping slug -> fonction de vue
DISPATCH_MAP = {
    "ressources-humaines": soumissions_rh,
    "garage": soumissions_garage,
}


def soumissions_dispatch(request, departement_slug):
    slug_norm = slugify(departement_slug).lower()
    view = DISPATCH_MAP.get(slug_norm)

    if view:
        return view(request, departement_slug)

    raise Http404(f"Page de soumissions non trouvée pour le département '{departement_slug}'.")


KPI_PERCENT_SLUGS = [
    "turnover-taux-de-roulement-du-personnel",
    "taux-de-fidelisation-des-clients-garage",
    "taux-restant",
    "taux-depart",
    "taux-non-fidelisation",
    "taux-atteinte-objectifs",
]


def page_tableau_bord(request, departement_slug):
    slug_norm = slugify(departement_slug).lower()
    departement_nom = DEPT_SLUG_TO_NAME.get(slug_norm, "Ressources humaines")

    today = now().date()
    current_year = today.year
    current_month = today.month

    # soumissions
    soumissions_qs = KPISubmission.objects.filter(
        kpi__departement=departement_nom,
        periode_annee=current_year,
        periode_mois=current_month,
    )
    total_soumissions = soumissions_qs.count()
    valides = soumissions_qs.filter(etat="Validée").count()
    taux_validation = round((valides / total_soumissions) * 100, 1) if total_soumissions else 0

    # mensuel
    monthly_data = KPISubmission.objects.filter(
        kpi__departement=departement_nom,
        periode_annee=current_year,
    ).values('periode_mois').annotate(
        total=Count('id'),
        valides=Count('id', filter=Q(etat='Validée')),
    )

    mois_labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
                   'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    submissions_series = [0] * 12
    validation_series = [0] * 12

    for entry in monthly_data:
        pm = entry.get('periode_mois')
        if pm is None:
            continue
        idx = pm - 1
        if 0 <= idx < 12:
            submissions_series[idx] = entry.get('total', 0) or 0
            if entry.get('total'):
                validation_series[idx] = round((entry.get('valides', 0) / entry['total']) * 100, 1)

    # variations de KPI
    all_submissions = KPISubmission.objects.filter(
        kpi__departement=departement_nom
    ).order_by('kpi_id', 'periode_annee', 'periode_mois', 'date_soumission')

    kpi_chart_data = defaultdict(lambda: {'labels': [], 'values': [], 'is_percent': False})

    for sub in all_submissions:
        kpi_name = sub.kpi.nom
        kpi_slug = slugify(kpi_name).lower()

        label = f"{sub.periode_mois}/{sub.periode_annee}"
        try:
            val = float(sub.valeur)
        except (TypeError, ValueError):
            continue

        kpi_chart_data[kpi_name]['labels'].append(label)
        kpi_chart_data[kpi_name]['values'].append(val)
        kpi_chart_data[kpi_name]['is_percent'] = kpi_slug in KPI_PERCENT_SLUGS

    context = {
        'pagename': 'tableau-bord',
        'departement_slug': departement_slug,
        'soumissions_count': total_soumissions,
        'taux_validation': taux_validation,
        'submissions_series': submissions_series,
        'validation_series': validation_series,
        'mois_labels': mois_labels,
        'kpi_chart_data': dict(kpi_chart_data),
    }
    return render(request, "departement/tableau_bord.html", context)

