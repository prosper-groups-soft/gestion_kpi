from django.db import models
from django.contrib.auth.models import User


DEPARTEMENTS = [
    ("Ressources humaines", "Ressources humaines"),
    ("Garage", "Garage"),
    ("Ventes", "Ventes"),
]


class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sexe = models.CharField(max_length=10, choices=[("Masculin", "Masculin"), ("Féminin", "Féminin")])
    date_naissance = models.DateField()
    numero_telephone = models.CharField(max_length=20)
    departement = models.CharField(max_length=50, choices=DEPARTEMENTS, default="SMQ")
    plain_password = models.CharField(max_length=128, help_text="Mot de passe en clair pour affichage interne")
    identifiant = models.CharField(max_length=128, default='')


    def __str__(self):
        return self.user.get_full_name()


class RapportKPI(models.Model):
    # Ex.: "Rapport IT Avril 2025.pdf"
    nom = models.CharField(max_length=255)

    departement = models.CharField(max_length=32, choices=DEPARTEMENTS)

    # Premier jour du mois concerné (permet filtres year/month)
    periode = models.DateField(help_text="Premier jour du mois du rapport")

    # Optionnel : plage d’historique utilisée pour l’analyse
    historique_de = models.DateField(null=True, blank=True)
    historique_a = models.DateField(null=True, blank=True)

    commentaires = models.TextField(blank=True)

    # Le PDF généré (on le traitera à l’étape 2)
    pdf = models.FileField(upload_to="rapports_kpi/", null=True, blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return self.nom

