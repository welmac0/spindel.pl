# Codes in the DB/API stay in English (stable contract).
# Translations are a separate layer - display only.
# Note: the major names below are my assumption based on the
# abbreviations - replace with official USOS names once you have access.

from models import ClassType, ListingStatus, Major

MAJOR_LABELS = {
    "pl": {
        Major.mat: "Matematyka",
        Major.iad: "Inżynieria i Analiza Danych",
        Major.iisi: "Informatyka i Systemy Informacyjne",
        Major.mad: "Matematyka i Analiza Danych",
    },
    "en": {
        Major.mat: "Mathematics",
        Major.iad: "Data Engineering and Analysis",
        Major.iisi: "Computer Science and Information Systems",
        Major.mad: "Mathematics and Data Analysis",
    },
}

CLASS_TYPE_LABELS = {
    "pl": {
        ClassType.cwi: "Ćwiczenia",
        ClassType.lab: "Laboratorium",
        ClassType.pro: "Projekt",
    },
    "en": {
        ClassType.cwi: "Tutorial",
        ClassType.lab: "Lab",
        ClassType.pro: "Project",
    },
}

STATUS_LABELS = {
    "pl": {
        ListingStatus.active: "Aktywne",
        ListingStatus.pending: "W trakcie",
        ListingStatus.closed: "Zamknięte",
    },
    "en": {
        ListingStatus.active: "Active",
        ListingStatus.pending: "Pending",
        ListingStatus.closed: "Closed",
    },
}