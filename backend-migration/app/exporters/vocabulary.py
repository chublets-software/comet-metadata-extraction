"""Identifiers used by the exporters.

Every Wikidata id below has a local twin in n4o-rse/chublets-wikibase-demo
(``data/csv/statements.csv``, property P4). An id is added here only when it has
been checked; anything else goes to the review list instead of being guessed.
"""

CHUBLET_CLASS = "Q141115627"
CHUBLETS_WIKIPROJECT = "Q141169143"
CHUBLETS_PLATFORM = "Q141115774"
GIT = "Q186055"

LANGUAGES = {"Python": "Q28865", "JavaScript": "Q2005"}
LICENCES = {"MIT": "Q334661", "GPL-2.0": "Q10513450"}

LOCAL_ITEMS = {
    CHUBLET_CLASS: "Q106",
    CHUBLETS_WIKIPROJECT: "Q108",
    CHUBLETS_PLATFORM: "Q109",
    GIT: "Q114",
    "Q28865": "Q370",
    "Q2005": "Q371",
    "Q334661": "Q369",
    "Q10513450": "Q934",
}

# background/property-set.csv of the demo; P854/P813 are the reference properties.
LOCAL_PROPERTIES = {
    "P31": "P2",
    "P275": "P107",
    "P277": "P123",
    "P348": "P148",
    "P356": "P114",
    "P361": "P122",
    "P1324": "P125",
    "P1401": "P138",
    "P2561": "P119",
    "P6104": "P118",
    "P8423": "P126",
    "P854": "P6",
    "P813": "P7",
}
