from django.db import models
from django.contrib.auth.models import User


class KPI(models.Model):
    DEPARTEMENTS = [
        ("Ressources humaines", "Ressources humaines"),
        ("Garage", "Garage"),
    ]
    FREQUENCE_CHOICES = [
        ("Mensuelle", "Mensuelle"),
        ("Trimestrielle", "Trimestrielle"),
        ("Semestrielle", "Semestrielle"),
        ("Annuelle", "Annuelle"),
    ]
    SOURCE_TYPE_CHOICES = [
        ("manuel", "Saisie manuelle"),
        ("fichier", "Fichier uploadé"),
        ("base", "Source base de données"),
    ]

    nom = models.CharField(max_length=255)
    formule = models.TextField(blank=True, null=True)
    frequence = models.CharField(max_length=20, choices=FREQUENCE_CHOICES, default='Mensuelle')
    departement = models.CharField(max_length=50, choices=DEPARTEMENTS)

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default="manuel")  # 🔹 Ajout

    # Champs de cible
    periode_annee = models.PositiveSmallIntegerField()
    periode_mois = models.PositiveSmallIntegerField(default=0, help_text="0 = pas de mois, sinon 1-12")
    valeur_cible = models.CharField(max_length=100)
    formule_mathjax = models.CharField(max_length=1024, default='', null=True)

    soumis_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="kpis_soumis")
    date_soumission = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ("nom", "departement", "periode_annee", "periode_mois")
        ordering = ["nom", "-periode_annee", "-periode_mois"]

    def __str__(self):
        mois_str = "N/A" if self.periode_mois == 0 else str(self.periode_mois)
        return f"{self.nom} ({self.departement}) - Cible: {self.valeur_cible} - {self.periode_annee}/{mois_str}"


class KPISubmission(models.Model):
    ETAT_CHOICES = [
        ("En attente", "En attente"),
        ("Validée", "Validée"),
        ("Rejetée", "Rejetée"),
    ]

    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="soumissions")
    valeur = models.CharField(max_length=255, blank=True, null=True)
    periode_annee = models.PositiveSmallIntegerField()
    periode_mois = models.PositiveSmallIntegerField(default=0, help_text="0 = pas de mois, sinon 1-12")

    # Nouveau champ : détails du calcul
    facteurs_utilises = models.JSONField(blank=True, null=True, help_text="Facteurs utilisés pour le calcul du KPI")

    # Nouveau champ : commentaire ou observation
    observation = models.TextField(blank=True, null=True)

    source_type = models.CharField(max_length=20, choices=KPI.SOURCE_TYPE_CHOICES, default="manuel")
    soumis_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True, null=True)
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default="En attente")

    class Meta:
        unique_together = ("kpi", "periode_annee", "periode_mois", "soumis_par")
        ordering = ["-date_soumission"]

    def __str__(self):
        return f"{self.kpi.nom} — {self.periode_annee}/{self.periode_mois} — {self.valeur}"

