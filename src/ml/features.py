"""
Unified feature extraction — merges utils.py and enhanced_features.py into one module.
Fixes: duplicate return statement, hardcoded lists, and duplicated red-flag logic.
"""

import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse
from collections import Counter

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Source credibility database
# ---------------------------------------------------------------------------
TRUSTED_SOURCES = frozenset({
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "bloomberg.com", "wsj.com", "ft.com", "economist.com",
    "npr.org", "pbs.org", "cnn.com", "abcnews.go.com",
    "cbsnews.com", "nbcnews.com", "usatoday.com", "latimes.com",
})

UNRELIABLE_SOURCES = frozenset({
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "yournewswire.com", "theonion.com", "clickhole.com",
})

TOPIC_KEYWORDS = {
    "politics": ["election", "president", "congress", "senate", "democrat", "republican", "vote", "policy", "government"],
    "health": ["health", "medical", "doctor", "disease", "vaccine", "treatment", "cure", "hospital", "patient"],
    "technology": ["technology", "tech", "software", "hardware", "ai", "artificial intelligence", "computer", "internet"],
    "science": ["science", "research", "study", "scientist", "experiment", "discovery", "laboratory"],
    "business": ["business", "economy", "stock", "market", "trade", "company", "corporate", "finance"],
    "entertainment": ["movie", "music", "celebrity", "film", "actor", "singer", "entertainment"],
}


def extract_features(text: str) -> Dict:
    """Extract linguistic features from raw text."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    total_words = len(text.split())
    avg_sent_length = total_words / len(sentences) if sentences else 0
    return {
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sent_length, 1),
        "question_count": text.count("?"),
        "exclamation_count": text.count("!"),
        "all_caps_count": len([w for w in text.split() if w.isupper() and len(w) > 1]),
        "total_words": total_words,
    }


def get_conspiracy_indicators(text: str) -> int:
    """Count conspiracy-theory language indicators."""
    keywords = [
        "cover up", "hidden truth", "secret", "conspiracy", "prove", "liar",
        "government lies", "fake news", "mainstream media", "deep state",
        "shadow government", "illuminati", "elite", "new world order",
    ]
    text_lower = text.lower()
    return sum(text_lower.count(kw) for kw in keywords)


def get_sensationalism_score(text: str) -> float:
    """Calculate normalized sensationalism score (0-1)."""
    words = [
        "shocking", "stunning", "exclusive", "breaking", "unbelievable",
        "incredible", "amazing", "horrible", "tragic", "devastating",
        "bombshell", "scandal", "massive", "huge", "enormous",
    ]
    text_lower = text.lower()
    count = sum(text_lower.count(w) for w in words)
    total = len(text.split())
    return (count / total) if total > 0 else 0.0


def extract_domain(text: str) -> str | None:
    """Extract the first domain from URLs found in text."""
    urls = re.findall(r"https?://(?:[a-zA-Z]|[0-9]|[$\-_@.&+]|[!*(),]|%[0-9a-fA-F]{2})+", text)
    if urls:
        parsed = urlparse(urls[0])
        return parsed.netloc.replace("www.", "")
    return None


def analyze_source(domain: str | None) -> Dict:
    """Analyze source credibility by domain."""
    if not domain:
        return {"credible": False, "reputation": 50, "category": "unknown"}
    domain = domain.lower()
    if any(t in domain for t in TRUSTED_SOURCES):
        return {"credible": True, "reputation": 95, "category": "trusted"}
    if any(u in domain for u in UNRELIABLE_SOURCES):
        return {"credible": False, "reputation": 10, "category": "unreliable"}
    return {"credible": False, "reputation": 50, "category": "unknown"}


def classify_topic(text: str) -> Tuple[str, float]:
    """Classify article topic with confidence score."""
    text_lower = text.lower()
    scores = {topic: sum(1 for kw in kws if kw in text_lower) for topic, kws in TOPIC_KEYWORDS.items()}
    total = sum(scores.values())
    if total == 0:
        return "general", 0.0
    best = max(scores, key=scores.get)
    return best, scores[best] / total


def highlight_suspicious_phrases(text: str) -> List[Dict]:
    """Identify and highlight suspicious phrases with severity levels."""
    patterns = [
        (r"\b(doctors don't want you to know|they don't want you to know)\b", "Medical Misinformation", "high"),
        (r"\b(this one weird trick|one simple trick)\b", "Clickbait", "high"),
        (r"\b(big pharma|mainstream media|deep state)\b", "Conspiracy Theory", "medium"),
        (r"\b(share before (it's |this is )?deleted|share now)\b", "Urgency Manipulation", "high"),
        (r"\b(shocking|breaking|exposed|revealed)\b", "Sensationalism", "low"),
        (r"\b(miracle cure|ancient remedy|secret ingredient)\b", "Medical Fraud", "high"),
        (r"[A-Z]{5,}", "Excessive Caps", "low"),
        (r"!{3,}", "Excessive Punctuation", "low"),
    ]
    findings = []
    for pattern, category, severity in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({"text": match.group(), "category": category, "severity": severity, "position": match.start()})
    return findings


def calculate_readability_score(text: str) -> Dict:
    """Calculate Flesch-Kincaid readability approximation."""
    sentences = text.count(".") + text.count("!") + text.count("?")
    words = len(text.split())
    if sentences == 0 or words == 0:
        return {"grade_level": 0, "difficulty": "Unknown", "avg_sentence_length": 0, "word_count": 0}
    avg_sl = words / sentences
    syllables = sum(1 for c in text if c.lower() in "aeiou")
    avg_syl = syllables / words if words > 0 else 0
    grade = max(0, min(18, 0.39 * avg_sl + 11.8 * avg_syl - 15.59))
    if grade < 6: diff = "Very Easy"
    elif grade < 9: diff = "Easy"
    elif grade < 12: diff = "Moderate"
    elif grade < 16: diff = "Difficult"
    else: diff = "Very Difficult"
    return {"grade_level": round(grade, 1), "difficulty": diff, "avg_sentence_length": round(avg_sl, 1), "word_count": words}


def detect_fake_news_red_flags(text: str) -> float:
    """Detect fake news red flags. Returns a score from 0.0 (clean) to 1.0 (all red flags)."""
    text_lower = text.lower()
    red_flags = 0.0
    max_flags = 10.0
    flag_patterns = [
        (r"doctors don't want you to know", 1), (r"this one weird trick", 1),
        (r"doctors hate|doctors are hiding", 1), (r"big pharma doesn't want", 1),
        (r"\bshare before (it's )?deleted", 1), (r"you won't believe what happened", 0.5),
        (r"click here|tap here", 0.5), (r"unbelievable what .* did", 0.5),
        (r"the (government|elite|illuminati|deep state) (is|are) (hiding|covering)", 1),
        (r"ancient (remedy|secret|cure)", 0.8),
    ]
    for pattern, weight in flag_patterns:
        if re.search(pattern, text_lower):
            red_flags += weight
    if text.count("!") > 3 or text.count("?") > 5:
        red_flags += 0.5
    if re.search(r"(allegedly|reportedly|apparently|supposedly|claims?).*?(found|discovered|revealed)", text_lower):
        if not re.search(r"(according to|researchers|scientists|studies)", text_lower):
            red_flags += 0.5
    return min(red_flags, max_flags) / max_flags


def extract_time_references(text: str) -> List[str]:
    """Extract time/date references from text."""
    patterns = [
        r"\b(yesterday|today|tomorrow)\b",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b(last|this|next)\s+(week|month|year)\b",
    ]
    refs = []
    for p in patterns:
        refs.extend(re.findall(p, text, re.IGNORECASE))
    return refs
