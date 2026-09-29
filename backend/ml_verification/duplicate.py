"""
Semantic Duplicate Detection Engine.
Uses sentence-transformers (all-MiniLM-L6-v2) to embed incoming report text and
compare cosine similarity against recent_events from the same city/state.
Rule:
Similarity > 0.85 AND same eventType -> mark DUPLICATE, set duplicateOfId.
Includes an in-memory embedding cache and a TF-IDF fallback for offline/air-gapped environments.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Try importing SentenceTransformer with graceful fallback
_ST_AVAILABLE = False
_st_model = None
_embedding_cache: Dict[str, np.ndarray] = {}

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except Exception:
    _ST_AVAILABLE = False


def _get_st_model():
    """Lazily loads SentenceTransformer('all-MiniLM-L6-v2') once."""
    global _st_model, _ST_AVAILABLE
    if _ST_AVAILABLE and _st_model is None:
        try:
            # Load lightweight, fast model
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            # If download fails or offline, fall back gracefully
            _ST_AVAILABLE = False
            _st_model = None
    return _st_model


def _compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D vectors."""
    dot = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _tfidf_fallback_similarity(text_a: str, text_b: str) -> float:
    """
    Fallback semantic similarity using character + word n-gram TF-IDF
    in case SentenceTransformer is not loaded or network is offline.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    try:
        vec = TfidfVectorizer(ngram_range=(1, 3), analyzer="char_wb")
        matrix = vec.fit_transform([text_a, text_b])
        dense = matrix.toarray()
        return _compute_cosine_similarity(dense[0], dense[1])
    except Exception:
        # Simplest set jaccard fallback
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)


def get_embedding(text: str) -> Optional[np.ndarray]:
    """Generates and caches text embedding."""
    if text in _embedding_cache:
        return _embedding_cache[text]

    model = _get_st_model()
    if model is not None:
        try:
            emb = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            _embedding_cache[text] = emb
            return emb
        except Exception:
            pass
    return None


def detect_duplicate(
    report: Dict[str, Any],
    target_event_type: str,
    recent_events: List[Dict[str, Any]],
    similarity_threshold: float = 0.85
) -> Tuple[bool, Optional[str], float]:
    """
    Detects if the incoming report is a duplicate of any existing recent event.
    Parameters:
      report: The incoming RawReport dict.
      target_event_type: The classified eventType of the incoming report.
      recent_events: List of recent WeatherEvent dicts.
      similarity_threshold: 0.85 per Shared Technical Contract.
    Returns:
      (is_duplicate: bool, duplicate_of_id: str | None, max_similarity: float)
    """
    if not recent_events or not isinstance(recent_events, list):
        return False, None, 0.0

    raw_text = report.get("rawText") or report.get("raw_text") or ""
    if not raw_text.strip():
        return False, None, 0.0

    report_city = str(report.get("city") or "").strip().lower()
    report_state = str(report.get("state") or "").strip().lower()

    # Pre-calculate embedding for incoming report text
    report_emb = get_embedding(raw_text)

    best_match_id = None
    max_sim = 0.0

    for event in recent_events:
        if not isinstance(event, dict):
            continue

        # Location matching: per contract, use city/state string matching
        event_city = str(event.get("city") or "").strip().lower()
        event_state = str(event.get("state") or "").strip().lower()

        # If both specify city and they don't match, skip
        if report_city and event_city and report_city != event_city:
            continue
        # If both specify state and they don't match, skip
        if report_state and event_state and report_state != event_state:
            continue

        # Must match same eventType
        candidate_event_type = event.get("eventType")
        if candidate_event_type != target_event_type:
            continue

        # Compute cosine similarity between texts
        candidate_text = event.get("rawText") or event.get("raw_text") or ""
        if not candidate_text.strip():
            continue

        sim = 0.0
        candidate_emb = get_embedding(candidate_text)

        if report_emb is not None and candidate_emb is not None:
            sim = _compute_cosine_similarity(report_emb, candidate_emb)
        else:
            # Fallback to TF-IDF n-gram cosine similarity
            sim = _tfidf_fallback_similarity(raw_text, candidate_text)

        if sim > max_sim:
            max_sim = sim
            best_match_id = event.get("id")

    is_dup = (max_sim >= similarity_threshold) and (best_match_id is not None)
    return is_dup, best_match_id if is_dup else None, round(max_sim, 3)
