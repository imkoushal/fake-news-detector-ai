"""
Canonical text preprocessing — the SINGLE source of truth.

Both training and inference MUST use this module so there is zero
train/serve skew.  The old codebase had 3 divergent copies of clean_text();
this module replaces all of them.
"""

import re
from typing import List

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# spaCy — optional but preferred for lemmatization
# ---------------------------------------------------------------------------
_nlp = None
_USE_SPACY = False

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    _USE_SPACY = True
    logger.info("spaCy model loaded successfully — using lemmatization")
except ImportError:
    logger.warning("spaCy not installed — falling back to regex-based preprocessing")
except OSError:
    logger.warning("spaCy model 'en_core_web_sm' not found — falling back to regex-based preprocessing")

# ---------------------------------------------------------------------------
# Stop-word set (used in both spaCy and fallback paths)
# ---------------------------------------------------------------------------
STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "can", "this",
    "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
    "what", "which", "who", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "just", "my", "your", "his", "her", "its", "our", "their",
    "am", "than", "very", "too", "also", "about", "up", "so", "if",
})

# Pre-compiled regexes for performance
_RE_URL = re.compile(r"http\S+|www\.\S+|[\w.-]+@[\w.-]+\.\w+", re.IGNORECASE)
_RE_HTML = re.compile(r"<[^>]+>")
_RE_MENTION_HASH = re.compile(r"@\w+|#")
_RE_NON_ALPHA = re.compile(r"[^a-z\s-]")
_RE_WHITESPACE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Deterministic text preprocessing pipeline.

    Steps:
      1. Lowercase
      2. Remove URLs, emails
      3. Remove HTML tags
      4. Remove @mentions and # symbols
      5. Remove non-alpha characters (keep letters, spaces, hyphens)
      6. Collapse whitespace
      7. Lemmatize (spaCy) or stop-word filter (fallback)
      8. Remove tokens shorter than 3 characters

    Parameters
    ----------
    text : str
        Raw article text.

    Returns
    -------
    str
        Cleaned, normalized text suitable for TF-IDF vectorization.
    """
    if not isinstance(text, str):
        text = str(text)

    text = text.lower()
    text = _RE_URL.sub(" ", text)
    text = _RE_HTML.sub(" ", text)
    text = _RE_MENTION_HASH.sub(" ", text)
    text = _RE_NON_ALPHA.sub(" ", text)
    text = _RE_WHITESPACE.sub(" ", text).strip()

    if _USE_SPACY and _nlp and text:
        try:
            doc = _nlp(text)
            tokens = [
                tok.lemma_
                for tok in doc
                if (
                    not tok.is_stop
                    and tok.is_alpha
                    and tok.lemma_ not in STOP_WORDS
                    and len(tok.lemma_) > 2
                )
            ]
            return " ".join(tokens).strip()
        except Exception:
            logger.debug("spaCy processing failed, using fallback", exc_info=True)

    # Fallback: simple stop-word removal
    tokens = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
    return " ".join(tokens).strip()


def extract_keywords(text: str, max_keywords: int = 5) -> str:
    """
    Extract salient keywords from text for web search queries.

    Prefers proper nouns and named entities, filters out common
    sentence-starting words that make poor search queries.
    """
    # Words that are capitalized but NOT useful search terms
    skip_words = {
        "the", "this", "that", "these", "those", "however", "although",
        "meanwhile", "furthermore", "moreover", "therefore", "because",
        "according", "also", "after", "before", "since", "while",
        "during", "about", "under", "over", "between", "through",
        "following", "including", "despite", "several", "many",
        "some", "new", "said", "says", "told", "added", "noted",
        "but", "and", "for", "not", "has", "have", "had", "was",
        "were", "are", "its", "his", "her", "our", "their",
        "who", "what", "when", "where", "why", "how", "all",
        "with", "from", "into", "will", "would", "could", "should",
        "may", "might", "can", "just", "still", "even", "only",
    }

    # Look for capitalized words (likely proper nouns / entities)
    cap_words = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text)

    # Filter out sentence-starting filler words
    meaningful = [w for w in cap_words if w.lower() not in skip_words]

    # Also look for acronyms (2+ uppercase letters) — e.g., DHS, ICE, FEMA, TSA
    acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
    acronym_skip = {"BREAKING", "UPDATE", "EXCLUSIVE", "URGENT", "ALERT", "NEW"}
    meaningful_acronyms = [a for a in acronyms if a not in acronym_skip and len(a) <= 6]

    # Combine: meaningful proper nouns first, then acronyms
    all_candidates = meaningful + meaningful_acronyms

    if not all_candidates:
        # Fallback: longest non-filler words
        words = re.findall(r"\w{4,}", text)
        all_candidates = [w for w in words if w.lower() not in skip_words]

    seen: set[str] = set()
    keywords: List[str] = []
    for w in all_candidates:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            keywords.append(w)
        if len(keywords) >= max_keywords:
            break

    return " ".join(keywords[:max_keywords])

