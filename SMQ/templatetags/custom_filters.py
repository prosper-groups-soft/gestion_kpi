from django import template
import os


register = template.Library()


@register.filter
def build_target_key(soumission):
    """
    Prend une instance de KPISubmission et retourne une clé de target sous forme de tuple.
    """
    return (
        soumission.kpi.id,
        soumission.periode_annee,
        soumission.periode_mois or 0,
        soumission.kpi.departement,
    )


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def filename(value):
    return os.path.basename(value)
