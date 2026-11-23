"""Offline disease feed loader."""
import json

from paths import resolve

CLASS_ORDER = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]
HIGH_CONCERN = {"mel", "bcc"}
FALLBACK_NAMES = {
    "akiec": "Actinic Keratosis",
    "bcc": "Basal Cell Carcinoma",
    "bkl": "Benign Keratosis / Seborrheic Keratosis",
    "df": "Dermatofibroma",
    "mel": "Malignant Melanoma",
    "nv": "Melanocytic Nevi",
    "vasc": "Vascular Lesions",
}


def load_feed() -> dict:
    with open(resolve("disease_feed.json"), encoding="utf-8") as f:
        return json.load(f)


def display_names(feed: dict) -> dict:
    names = dict(FALLBACK_NAMES)
    for p in feed.get("posts", []):
        names[p["class_code"]] = p.get("class_name", names.get(p["class_code"], p["class_code"]))
    return names
