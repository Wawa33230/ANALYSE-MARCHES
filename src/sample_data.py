"""Jeu de donnees de DEMONSTRATION (fictif mais realiste).

Permet de visualiser le tableau de bord sans connexion (commande : --demo).
Contient des cas representatifs : la cible parfaite (type France Loire), un marche
carrelage (signale), un marche chauffage (hors cible), etc.
"""

from .models import Tender

SAMPLE = [
    Tender(
        id="demo:1",
        reference="2026020",
        source="BOAMP",
        title="Accord-cadre a bons de commande - Travaux d'entretien courant des logements "
              "en electricite, plomberie et menuiseries - Lot 01 Plomberie Travaux d'Accessibilite",
        buyer="France Loire (Office Public de l'Habitat)",
        department="45, 18",
        market_type="Accord-cadre - bons de commande - multi-attributaires",
        cpv=["45330000", "45332400"],
        publication_date="2026-06-04",
        deadline="2026-09-25",
        url="https://www.boamp.fr/",
        description="Remplacement de baignoire par bac a douche extra plat, adaptation PMR, "
                    "barre de maintien, panneaux muraux type Kinewall sans percement (amiante SS4).",
    ),
    Tender(
        id="demo:2",
        reference="2026-AC-LOGI-07",
        source="TED (UE)",
        title="Adaptation de salles de bains pour le maintien a domicile - Remplacement "
              "baignoire/douche et pose de receveurs extra-plats",
        buyer="Logiouest - ESH",
        department="44, 49, 72",
        market_type="Avis europeen (> seuils)",
        cpv=["45211310", "45330000"],
        publication_date="2026-06-18",
        deadline="2026-09-06",
        url="https://ted.europa.eu/",
        description="Accessibilite PMR, douche securisee, barre de relevage, habillage mural panneaux.",
    ),
    Tender(
        id="demo:3",
        reference="TH-2026-037-SDB",
        source="BOAMP",
        title="Marche de renovation de salles de bains avec pose de carrelage et faience murale",
        buyer="Tours Habitat",
        department="37",
        market_type="Procedure adaptee (MAPA)",
        cpv=["45431000"],
        publication_date="2026-06-20",
        deadline="2026-09-02",
        url="https://www.boamp.fr/",
        description="Depose baignoire, douche, mais habillage exclusivement en carrelage et faience.",
    ),
    Tender(
        id="demo:4",
        reference="GDH-CHAUF-2026",
        source="BOAMP",
        title="Maintenance des chaufferies collectives et reseau de chaleur - contrat de chauffage",
        buyer="Grand Dijon Habitat",
        department="21",
        market_type="Accord-cadre",
        cpv=["50721000"],
        publication_date="2026-06-15",
        deadline="2026-09-30",
        url="https://www.boamp.fr/",
        description="Entretien chaudieres gaz, desembouage, production d'eau chaude collective.",
    ),
    Tender(
        id="demo:5",
        reference="MPI-1845210",
        source="marches-publics.info",
        title="Travaux d'accessibilite des logements - amenagement de douches PMR",
        buyer="Vendee Habitat",
        department="85",
        market_type="Plateforme (flux)",
        cpv=[],
        publication_date="2026-06-25",
        deadline="2026-09-15",
        url="https://www.marches-publics.info/",
        description="Remplacement baignoire en douche, receveur extra plat, mitigeur thermostatique.",
    ),
    Tender(
        id="demo:6",
        reference="LFG-PLOMB-2026-12",
        source="BOAMP",
        title="Entretien courant plomberie sanitaire du patrimoine - lavabos, WC, robinetterie",
        buyer="SA HLM Le Logis Familial",
        department="35",
        market_type="Accord-cadre - bons de commande",
        cpv=["45330000"],
        publication_date="2026-06-10",
        deadline="2026-08-12",
        url="https://www.boamp.fr/",
        description="Plomberie sanitaire courante : reparations, remplacement de robinetterie, debouchage.",
    ),
]


def fetch_demo():
    # On renvoie des copies pour ne pas muter le module
    import copy
    return [copy.deepcopy(t) for t in SAMPLE]
