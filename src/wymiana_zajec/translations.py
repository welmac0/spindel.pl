# Codes in the DB/API stay in English (stable contract).
# Translations are a separate layer - display only.
# Major labels are intentionally short and neutral; codes remain the API contract.

from wymiana_zajec.models import ClassType, ListingStatus, Major

MAJOR_LABELS = {
    "pl": {
        Major.mat: "Mat",
        Major.iad: "IiAD",
        Major.iisi: "IiSI",
        Major.mad: "MAD",
        Major.cs: "CS",
    },
    "en": {
        Major.mat: "Mat",
        Major.iad: "IiAD",
        Major.iisi: "IiSI",
        Major.mad: "MAD",
        Major.cs: "CS",
    },
}

CLASS_TYPE_LABELS = {
    "pl": {
        ClassType.cwi: "Ćwiczenia",
        ClassType.lab: "Laby",
        ClassType.pro: "Projekt",
    },
    "en": {
        ClassType.cwi: "Tutorial",
        ClassType.lab: "labs",
        ClassType.pro: "project",
    },
}

STATUS_LABELS = {
    "pl": {
        ListingStatus.active: "Aktywne",
        ListingStatus.pending: "W trakcie",
        ListingStatus.fulfilled: "Zrealizowane",
        ListingStatus.stale: "Nieaktualne",
        ListingStatus.cancelled: "Anulowane",
    },
    "en": {
        ListingStatus.active: "Active",
        ListingStatus.pending: "Pending",
        ListingStatus.fulfilled: "Fulfilled",
        ListingStatus.stale: "Stale",
        ListingStatus.cancelled: "Cancelled",
    },
}