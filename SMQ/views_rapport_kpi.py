import matplotlib
matplotlib.use('Agg')  # <-- backend non-GUI
import matplotlib.pyplot as plt

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from .models import RapportKPI
import io
from datetime import datetime
from django.shortcuts import redirect
from django.core.files.base import ContentFile
from Departement.models import KPI
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import requests
from textwrap import wrap
from django.contrib.staticfiles import finders
import re
from django.http import FileResponse, Http404
from django.conf import settings
import os
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.colors import black



OPENROUTER_API_KEY = "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"


# Chemin du logo (static)
LOGO_PATH = finders.find("images/auto-lubumbashi-logo.webp")


# Mois FR pour le template (1..12)
MONTHS_FR = [
    (1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
    (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
    (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre"),
]


def rapports_kpi(request):
    q = request.GET.get("q", "").strip()
    year_filter = request.GET.get("year", "").strip()
    month_filter = request.GET.get("month", "").strip()
    page_number = request.GET.get("page", 1)

    qs = RapportKPI.objects.all()

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(departement__icontains=q) |
            Q(commentaires__icontains=q)
        )

    if year_filter:
        qs = qs.filter(periode__year=year_filter)

    if month_filter:
        try:
            qs = qs.filter(periode__month=int(month_filter))
        except ValueError:
            pass

    paginator = Paginator(qs.order_by("-generated_at"), 10)
    page_obj = paginator.get_page(page_number)

    # Années disponibles (dynamiques) pour la liste déroulante
    years = RapportKPI.objects.dates("periode", "year", order="DESC")

    context = {
        "page_obj": page_obj,
        "search_query": q,
        "year_filter": year_filter,
        "month_filter": month_filter,
        "years": years,
        "months": MONTHS_FR,
        "pagename": "rapports-kpi",
    }
    return render(request, "smq/rapport_kpi.html", context)


def delete_rapport_kpi(request, pk: int):
    rapport = get_object_or_404(RapportKPI, pk=pk)
    # Supprime physiquement le PDF s'il existe
    if rapport.pdf:
        rapport.pdf.delete(save=False)
    rapport.delete()
    messages.success(request, "Rapport supprimé avec succès.")
    return redirect(request.META.get("HTTP_REFERER", reverse("smq/rapports-kpi")))


def generate_rapport_kpi(request):
    if request.method != "POST":
        return redirect("smq/rapports-kpi")

    # --- Récupération des paramètres ---
    mois_str = request.POST.get("mois")
    historique_de = request.POST.get("historique_de") or None
    historique_a = request.POST.get("historique_a") or None
    commentaires = request.POST.get("commentaires", "")

    if not mois_str:
        messages.error(request, "La période est requise.")
        return redirect(request.META.get("HTTP_REFERER"))

    mois_map = {nm: m for m, nm in MONTHS_FR}
    mois = mois_map.get(mois_str)
    if not mois:
        messages.error(request, "Mois invalide.")
        return redirect(request.META.get("HTTP_REFERER"))

    annee = datetime.now().year

    # --- Récupération des KPI et historique ---
    kpis = KPI.objects.all()
    kpi_data = []

    for k in kpis:
        try:
            valeur_cible = float(str(k.valeur_cible).replace(',', '.'))
        except (ValueError, TypeError):
            valeur_cible = 0.0

        soumissions_qs = k.soumissions.all()

        if historique_de and historique_a:
            try:
                date_debut = datetime.strptime(historique_de, "%Y-%m-%d")
                date_fin = datetime.strptime(historique_a, "%Y-%m-%d")
                soumissions_qs = soumissions_qs.filter(
                    periode_annee__gte=date_debut.year,
                    periode_annee__lte=date_fin.year,
                    periode_mois__gte=date_debut.month if date_debut.year == date_fin.year else 1,
                    periode_mois__lte=date_fin.month if date_fin.year == date_fin.year else 12,
                )
            except ValueError:
                pass
        else:
            soumissions_qs = soumissions_qs.filter(
                periode_annee=annee,
                periode_mois=mois
            )

        historique_valeurs = []
        for s in soumissions_qs.order_by("periode_annee", "periode_mois"):
            try:
                valeur_reelle = float(str(s.valeur).replace(',', '.')) if s.valeur else 0.0
            except ValueError:
                valeur_reelle = 0.0
            historique_valeurs.append({
                "annee": s.periode_annee,
                "mois": s.periode_mois,
                "valeur_reelle": valeur_reelle,
                "facteurs_utilises": s.facteurs_utilises or {},
                "observation": s.observation or "",
            })

        kpi_data.append({
            "nom": k.nom,
            "departement": k.departement,
            "valeur_cible": valeur_cible,
            "historique": historique_valeurs,
        })

    if not kpi_data:
        messages.error(request, "Aucun KPI disponible pour cette période.")
        return redirect(request.META.get("HTTP_REFERER"))

    # --- Préparer les données pour le LLM ---
    departements = sorted(list(set([k["departement"] for k in kpi_data])))
    llm_struct = []
    for dept in departements:
        dept_kpis = [k for k in kpi_data if k["departement"] == dept]
        kpis_struct = [{"nom": k["nom"], "valeur_cible": k["valeur_cible"], "historique": k["historique"]} for k in dept_kpis]
        llm_struct.append({"departement": dept, "kpis": kpis_struct})

    # --- Préparer le prompt LLM ---
    prompt = f"""
Vous êtes un analyste de données expérimenté chargé de rédiger un rapport d'analyse des KPI.
Le rapport doit être rédigé en Markdown, avec des titres de section de niveau 2 (##).
Ne pas inclure de données brutes comme "Valeur cible" ou "Historique" dans le texte, concentrez-vous sur l'interprétation.

Données disponibles (période {mois_str}/{annee}) :
{llm_struct}

Commentaires internes (à utiliser uniquement pour l'interprétation) :
{commentaires if commentaires else 'Aucun commentaire fourni.'}
"""

    # --- Appel LLM ---
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            }
        )
        print(response.json())
        response.raise_for_status()
        llm_text = response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        messages.error(request, f"Erreur lors de l'appel à l'API : {e}")
        return redirect(request.META.get("HTTP_REFERER"))
    except (KeyError, IndexError) as e:
        messages.error(request, f"Réponse de l'API inattendue : {e}")
        return redirect(request.META.get("HTTP_REFERER"))

    # --- Création du PDF ---
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    margin = 60
    y_position = height - margin

    styles = getSampleStyleSheet()
    styles['Heading2'].fontName = 'Helvetica-Bold'
    styles['Heading2'].fontSize = 14
    styles['Heading2'].leading = 16
    styles['Heading2'].spaceAfter = 12

    styles['Heading3'].fontName = 'Helvetica-BoldOblique'
    styles['Heading3'].fontSize = 12
    styles['Heading3'].leading = 14
    styles['Heading3'].spaceAfter = 8

    styles['BodyText'].fontName = 'Helvetica'
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 12
    styles['BodyText'].spaceAfter = 6
    styles['BodyText'].alignment = TA_JUSTIFY

    def draw_paragraph(c, text, style, y_pos):
        # Convertir les listes Markdown en listes HTML pour ReportLab
        text = re.sub(r'^\s*-\s*', r'<li>', text, flags=re.MULTILINE)
        text = '<ul>' + text + '</ul>' if '<li>' in text else text

        P = Paragraph(text, style)
        w, h = P.wrap(width - 2 * margin, height)
        if y_pos - h < margin:
            c.showPage()
            y_pos = height - margin
            try:
                logo = ImageReader(LOGO_PATH)
                c.drawImage(logo, width - margin - 120, height - 70, width=100, height=50, preserveAspectRatio=True)
            except Exception:
                pass
            c.setFont("Helvetica-Bold", 18)
            c.drawString(margin, height - 50, "Rapport d'analyse des KPI (suite)")
            c.setFont("Helvetica", 12)
            c.drawString(margin, height - 70, f"Période: {mois_str} {annee}")
            c.line(margin, height - 80, width - margin, height - 80)
            y_pos -= 100
        P.drawOn(c, margin, y_pos - h)
        y_pos -= h + 15
        return y_pos

    # --- En-tête PDF ---
    try:
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, width - margin - 120, height - 70, width=100, height=50, preserveAspectRatio=True)
    except Exception:
        pass
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, height - 50, "Rapport d'analyse des KPI")
    c.setFont("Helvetica", 12)
    c.drawString(margin, height - 70, f"Période: {mois_str} {annee}")
    c.line(margin, height - 80, width - margin, height - 80)
    y_position -= 100

    # --- Traitement et dessin du contenu LLM ---
    # Nettoyer le texte des titres markdown (`#` et `##`)
    llm_text = re.sub(r'^\s*#+\s*', '', llm_text, flags=re.MULTILINE)
    
    # Séparer le texte en paragraphes pour l'afficher
    paragraphs = llm_text.split('\n\n')
    for p_text in paragraphs:
        if p_text.strip():
            y_position = draw_paragraph(c, p_text.strip(), styles['BodyText'], y_position)

    # --- Analyse par département et KPI (ajout des graphiques) ---
    for dept in departements:
        dept_kpis = [k for k in kpi_data if k["departement"] == dept]
        y_position = draw_paragraph(c, f"Analyse pour le département : {dept}", styles['Heading2'], y_position)

        for k in dept_kpis:
            y_position = draw_paragraph(c, k['nom'], styles['Heading3'], y_position)

            hist = k["historique"]
            if hist:
                x_vals = [f"{h['mois']}/{h['annee']}" for h in hist]
                y_vals = [h['valeur_reelle'] for h in hist]
                cible = k['valeur_cible']

                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(x_vals, y_vals, marker='o', label='Réel', color='#007bff')
                ax.axhline(y=cible, color='red', linestyle='--', label='Cible')
                ax.set_title(f"{k['nom']} - Historique", fontsize=10)
                ax.set_ylabel("Valeur")
                ax.set_xticks(range(len(x_vals)))
                ax.set_xticklabels(x_vals, rotation=45, ha='right', fontsize=8)
                ax.legend(fontsize=8)
                ax.grid(axis='y', linestyle='--', alpha=0.5)
                plt.tight_layout()

                buf = io.BytesIO()
                plt.savefig(buf, format='PNG', dpi=150)
                plt.close(fig)
                buf.seek(0)
                img = ImageReader(buf)
                if y_position - 180 < margin:
                    c.showPage()
                    y_position = height - margin
                c.drawImage(img, margin, y_position - 180, width=width - 2 * margin, height=180)
                y_position -= 200

    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    # --- Enregistrement PDF ---
    pdf_file = ContentFile(pdf_buffer.read(), name=f"rapport_kpi_{annee}_{mois}.pdf")
    RapportKPI.objects.create(
        nom=f"Rapport KPI {mois_str} {annee}",
        departement="Tous",
        periode=datetime(annee, mois, 1),
        historique_de=historique_de,
        historique_a=historique_a,
        commentaires=commentaires,
        pdf=pdf_file
    )

    messages.success(request, "Rapport KPI généré avec succès !")
    return redirect(request.META.get("HTTP_REFERER"))


def view_pdf(request, filename):
    filepath = os.path.join(settings.MEDIA_ROOT, 'rapports_kpi', filename)
    if not os.path.exists(filepath):
        raise Http404("Fichier non trouvé")
    response = FileResponse(open(filepath, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['X-Frame-Options'] = 'SAMEORIGIN'  # crucial pour iframe
    return response
