"""
Weather Event Classification Engine.
Hybrid architecture:
1. Primary: Lightweight TF-IDF + Logistic Regression trained on bilingual weather texts.
2. Fallback / Disambiguation: Keyword/rule-based matching for English + Hindi (Devanagari + Hinglish).
Always returns a valid (eventType, confidence) tuple without throwing exceptions.
"""

import os
import re
from pathlib import Path
from typing import Tuple, Dict, Any, List
import joblib

# Valid categories defined by Shared Technical Contract
VALID_EVENT_TYPES = [
    "RAINFALL",
    "THUNDERSTORM",
    "FLOODING",
    "HEATWAVE",
    "FOG",
    "DUST_STORM",
    "STRONG_WIND",
    "UNKNOWN",
]

# Bilingual Keyword Dictionary (English + Hindi Devanagari + Common Transliterations)
EVENT_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "FLOODING": {
        "en": [
            "flood", "flooding", "flooded", "waterlogging", "waterlogged",
            "submerged", "inundated", "inundation", "overflow", "overflowing",
            "underwater", "deluge", "water stagnation", "marooned"
        ],
        "hi_dev": ["बाढ़", "जलभराव", "जलमग्न", "डूब", "सैलाब", "उफान", "पानी भर"],
        "hi_trans": ["baadh", "badh", "jalbhirav", "jalbharav", "paani bhar", "pani bhar", "doob", "dhoob", "sailab"]
    },
    "THUNDERSTORM": {
        "en": [
            "thunder", "thunderstorm", "lightning", "lightning strike", "thunderclap",
            "cloudburst", "hail", "hailstorm", "hailstones", "electrical storm", "squall"
        ],
        "hi_dev": ["बिजली", "गरज", "तड़ित", "ओले", "ओलावृष्टि", "कड़क", "आकाशीय"],
        "hi_trans": ["bijli", "garaj", "badal garaj", "ole", "olavrishti", "toofan"]
    },
    "HEATWAVE": {
        "en": [
            "heatwave", "heat wave", "scorching", "sweltering", "blistering",
            "extreme heat", "sunstroke", "boiling", "heat index", "mercury touches",
            "thermal stress", "furnace"
        ],
        "hi_dev": ["लू", "भीषण गर्मी", "तपन", "तपिश", "गर्म हवा", "प्रचंड गर्मी", "झुलसा"],
        "hi_trans": ["loo", "garmi", "bheeshan garmi", "tapan", "tapish", "dhoop", "garm hawayen"]
    },
    "FOG": {
        "en": [
            "dense fog", "fog", "foggy", "mist", "smog", "zero visibility",
            "low visibility", "haze", "fog lights", "shrouding", "white mist"
        ],
        "hi_dev": ["कोहरा", "धुंध", "कुहासा", "विजिबिलिटी", "दृश्यता"],
        "hi_trans": ["kohra", "dense kohra", "dhundh", "kuhasa", "fog"]
    },
    "DUST_STORM": {
        "en": [
            "dust storm", "duststorm", "sandstorm", "sand storm", "dust gale",
            "haboob", "dusty", "sand grit", "particulate wall", "dust wall"
        ],
        "hi_dev": ["धूल भरी आंधी", "रेत का तूफान", "धूल का तूफान", "रेतीला तूफान", "अंधी"],
        "hi_trans": ["aandhi", "dhool bhari aandhi", "andhi", "dhool", "ret ka toofan", "sandstorm"]
    },
    "STRONG_WIND": {
        "en": [
            "strong wind", "gale", "high winds", "wind gust", "gusty winds",
            "cyclonic winds", "windstorm", "tempest", "howling wind", "uprooted tree",
            "blown off"
        ],
        "hi_dev": ["तूफानी हवा", "तेज हवा", "हवा के झोंके", "चक्रवाती हवा", "हवा की गति"],
        "hi_trans": ["tez hawa", "toofani hawa", "hawa ke jhonke", "gale force", "wind gust"]
    },
    "RAINFALL": {
        "en": [
            "rain", "raining", "downpour", "drizzle", "drizzling", "shower",
            "monsoon", "torrential", "precipitation", "wet", "drenching", "pouring"
        ],
        "hi_dev": ["बारिश", "वर्षा", "बरसात", "बूंदाबांदी", "झमाझम", "मूसलाधार", "रिमझिम"],
        "hi_trans": ["barish", "baarish", "barsaat", "varsha", "bundabandi", "rimjhim"]
    }
}


class WeatherClassifier:
    """Hybrid Classifier combining TF-IDF + Logistic Regression with Rule/Keyword Fallbacks."""

    def __init__(self):
        self._vectorizer = None
        self._model = None
        self._loaded = False
        self._load_models()

    def _load_models(self):
        """Loads model artifacts using strictly relative paths."""
        try:
            base_dir = Path(__file__).resolve().parent
            vec_path = base_dir / "models" / "tfidf_vectorizer.joblib"
            model_path = base_dir / "models" / "event_classifier.joblib"

            if vec_path.exists() and model_path.exists():
                self._vectorizer = joblib.load(vec_path)
                self._model = joblib.load(model_path)
                self._loaded = True
        except Exception:
            # Fallback gracefully to purely rule-based if models fail to load
            self._loaded = False

    def _keyword_rule_classify(self, text: str) -> Tuple[str, float, int]:
        """
        Scans text for English and Hindi weather keywords.
        Returns: (best_category, heuristic_confidence, match_count)
        """
        lower_text = text.lower()
        scores: Dict[str, int] = {cat: 0 for cat in EVENT_KEYWORDS}

        for cat, lang_dict in EVENT_KEYWORDS.items():
            for kw in lang_dict.get("en", []):
                if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                    # Multi-word matches carry higher weight
                    scores[cat] += 2 if " " in kw else 1

            for kw in lang_dict.get("hi_dev", []):
                if kw in text:
                    scores[cat] += 2

            for kw in lang_dict.get("hi_trans", []):
                if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
                    scores[cat] += 2 if " " in kw else 1

        best_cat = max(scores, key=scores.get)
        match_count = scores[best_cat]

        if match_count == 0:
            return "UNKNOWN", 0.30, 0

        # Heuristic confidence based on match richness
        conf = min(0.95, 0.65 + (match_count * 0.10))
        return best_cat, round(conf, 3), match_count

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classifies incoming report text into one of the 7 WeatherEvent categories.
        Guaranteed to return (eventType, confidence) without throwing exceptions.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return "UNKNOWN", 0.0

        clean_text = text.strip()

        # Step 1: Run keyword matching
        rule_cat, rule_conf, rule_matches = self._keyword_rule_classify(clean_text)

        # Step 2: Run ML model if loaded
        if self._loaded and self._vectorizer and self._model:
            try:
                features = self._vectorizer.transform([clean_text])
                probabilities = self._model.predict_proba(features)[0]
                classes = self._model.classes_

                best_idx = probabilities.argmax()
                ml_cat = classes[best_idx]
                ml_conf = float(probabilities[best_idx])

                # Disambiguation / Blending Logic:
                # 1. FLOODING vs RAINFALL: "waterlogging/submerged" is specifically FLOODING
                if rule_matches > 0 and rule_cat == "FLOODING" and ml_cat == "RAINFALL":
                    return "FLOODING", round(max(rule_conf, ml_conf), 3)

                # 2. THUNDERSTORM vs RAINFALL: "lightning/thunder" is specifically THUNDERSTORM
                if rule_matches > 0 and rule_cat == "THUNDERSTORM" and ml_cat == "RAINFALL":
                    return "THUNDERSTORM", round(max(rule_conf, ml_conf), 3)

                # 3. DUST_STORM vs STRONG_WIND: "sand/dust" is specifically DUST_STORM
                if rule_matches > 0 and rule_cat == "DUST_STORM" and ml_cat == "STRONG_WIND":
                    return "DUST_STORM", round(max(rule_conf, ml_conf), 3)

                # 4. If ML is confident (>= 0.50), trust ML
                if ml_conf >= 0.50:
                    return ml_cat, round(ml_conf, 3)

                # 5. If ML confidence is lower (< 0.50), fall back to keyword rule if available
                if rule_matches > 0:
                    return rule_cat, round(rule_conf, 3)

                # 6. Fall back to ML best guess rather than returning UNKNOWN
                return ml_cat, round(max(ml_conf, 0.40), 3)

            except Exception:
                # In case of any ML transform/predict anomaly, fall back to rule
                pass

        # If model is not loaded or failed:
        if rule_matches > 0:
            return rule_cat, round(rule_conf, 3)

        # Never return UNKNOWN silently on actual text, provide best guess with low confidence
        return "RAINFALL", 0.35


# Singleton instance
_classifier_instance = None

def get_classifier() -> WeatherClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = WeatherClassifier()
    return _classifier_instance
