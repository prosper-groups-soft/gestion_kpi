import pandas as pd


def generer_fichier_excel_garage(path: str):
    data = {
        "ClientID": [f"C{i:03d}" for i in range(1, 21)],
        "EstRevenuPourEntretien": [
            "Oui", "Non", "Non", "Non", "Non", "Non", "Non", "Non", "Non", "Non",
            "Non", "Non", "Non", "Non", "Non", "Non", "Non", "Non", "Oui", "Non"
        ],
        "EstPrévuProchainEntretien": [
            "Non", "Non", "Non", "Oui", "Non", "Non", "Non", "Non", "Oui", "Non",
            "Non", "Non", "Non", "Oui", "Non", "Non", "Non", "Non", "Non", "Non"
        ]
    }
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)
    print(f"Fichier Excel généré à : {path}")


# Exemple d'appel
generer_fichier_excel_garage("garage_clients_entretien.xlsx")

