from django import template


register = template.Library()


@register.filter
def dict_get(d, key):
    return d.get(key)


@register.filter
def replace_chars(value, chars_to_replace):
    """
    Remplace tous les caractères de chars_to_replace par un espace.
    Ex: "nbre_depart/total" | replace_chars:"_/"
    """
    for c in chars_to_replace:
        value = value.replace(c, " ")
    return value


@register.filter
def maybe_percent(d, key):
    """
    Retourne la valeur avec % si nécessaire.
    d = dict de facteurs
    key = clé
    """
    val = d.get(key)
    keys_with_percent = [
        "taux_turnover", 
        "taux_restant",
        "taux_depart", 
        "taux_fidelisation", 
        "taux_non_fidelisation",
        "taux_atteinte_objectifs"
    ]
    if key in keys_with_percent:
        return f"{val} %"
    return val



@register.filter
def replace_character(value, args):
    """
    Remplace des caractères dans une chaîne.
    args doit être au format "ancien,nouveau"
    Exemple : "_,-" remplacera _ par -
    """
    try:
        old, new = args.split(",")
        return str(value).replace(old, new)
    except ValueError:
        # si mauvais format, retourne la valeur brute
        return value

