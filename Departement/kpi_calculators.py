from abc import ABC, abstractmethod


# Base abstraite
class KpiCalculator(ABC):
    def __init__(self, periode_annee, periode_mois=None):
        self.periode_annee = periode_annee
        self.periode_mois = periode_mois

    @abstractmethod
    def calculate(self, **kwargs):
        """
        Calcule et retourne la valeur du KPI.
        Les données nécessaires sont passées dans kwargs.
        """
        pass


class TauxFidelisationGarage(KpiCalculator):
    def calculate(self, **kwargs):
        nbre_clients_revenus = kwargs.get("nbre_clients_revenus", 0)
        nbre_clients_prevu = kwargs.get("nbre_clients_prevu", 0)
        df_clients = kwargs.get("df_clients")  # le dataframe complet

        if df_clients is not None:
            # compter les clients qui étaient prévus ET revenus
            revenus_et_prevu = df_clients[
                (df_clients["EstRevenuPourEntretien"].str.lower() == "oui") &
                (df_clients["EstPrévuProchainEntretien"].str.lower() == "oui")
            ].shape[0]
            nbre_clients_prevu = df_clients[df_clients["EstPrévuProchainEntretien"].str.lower() == "oui"].shape[0]
            taux = (revenus_et_prevu / nbre_clients_prevu * 100) if nbre_clients_prevu else 0
        else:
            # fallback : ancien calcul
            taux = (nbre_clients_revenus / nbre_clients_prevu * 100) if nbre_clients_prevu else 0

        return round(taux, 2)


class TurnoverRH(KpiCalculator):
    def calculate(self, **kwargs):
        nbre_depart = kwargs.get("nbre_depart", 0)
        effectif_total = kwargs.get("effectif_total", 0)

        if effectif_total == 0:
            return 0

        taux = (nbre_depart / effectif_total) * 100
        return round(taux, 2)


class TauxAtteinteObjectifsVente(KpiCalculator):
    def calculate(self, **kwargs):
        nbre_branches_objectif_atteint = kwargs.get("nbre_branches_objectif_atteint", 0)
        nbre_total_branches = kwargs.get("nbre_total_branches", 0)

        if nbre_total_branches == 0:
            return 0

        taux = (nbre_branches_objectif_atteint / nbre_total_branches) * 100
        return round(taux, 2)


KPI_CALCULATORS = {
    "Taux de fidélisation des clients Garage": TauxFidelisationGarage,
    "Turnover/ Taux de roulement du personnel": TurnoverRH,
    "Taux d'atteinte des objectifs de vente": TauxAtteinteObjectifsVente,
}


def calculer_valeur_kpi(kpi_obj, periode_annee, periode_mois=None, **kwargs):
    calc_class = KPI_CALCULATORS.get(kpi_obj.nom)
    if not calc_class:
        raise NotImplementedError(f"Calculateur non défini pour le KPI '{kpi_obj.nom}'")
    calculator = calc_class(periode_annee, periode_mois)
    return calculator.calculate(**kwargs)


# -------------------------
# Exemple d'utilisation fictive dans une vue Django

# Supposons que tu as un modèle KPI et des données dans ta base,
# tu peux faire comme suit pour calculer et soumettre un KPI :

def exemple_calcul_et_soumission_kpi(request, kpi_obj, periode_annee, periode_mois=None):
    # Exemple : récupération des données métier dans la base (à adapter)
    if kpi_obj.nom == "Taux de fidélisation des clients Garage":
        nbre_clients_revenus = 120  # Exemple, à récupérer avec ORM
        nbre_clients_prevu = 150    # Exemple, à récupérer avec ORM

        valeur = calculer_valeur_kpi(
            kpi_obj,
            periode_annee,
            periode_mois,
            nbre_clients_revenus=nbre_clients_revenus,
            nbre_clients_prevu=nbre_clients_prevu
        )

    elif kpi_obj.nom == "Turnover/ Taux de roulement du personnel":
        nbre_depart = 5
        effectif_total = 100

        valeur = calculer_valeur_kpi(
            kpi_obj,
            periode_annee,
            periode_mois,
            nbre_depart=nbre_depart,
            effectif_total=effectif_total
        )

    elif kpi_obj.nom == "Taux d'atteinte des objectifs de vente":
        nbre_branches_objectif_atteint = 8
        nbre_total_branches = 10

        valeur = calculer_valeur_kpi(
            kpi_obj,
            periode_annee,
            periode_mois,
            nbre_branches_objectif_atteint=nbre_branches_objectif_atteint,
            nbre_total_branches=nbre_total_branches
        )

    else:
        valeur = None

    # Ici tu peux enregistrer cette valeur dans la table KPISubmission par exemple
    # KPISubmission.objects.create(kpi=kpi_obj, periode_annee=periode_annee, periode_mois=periode_mois, valeur=valeur, soumis_par=request.user, etat="En attente")

    return valeur

