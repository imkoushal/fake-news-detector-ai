# utils.py - Hybrid Text Processing for Fake News Detection
import re
import spacy

# Load spaCy model once (if available)
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser"])
    USE_SPACY = True
except Exception:
    nlp = None
    USE_SPACY = False

# Enhanced stopwords list
ENHANCED_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'not', 'only', 'just', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
}

def clean_text(text: str) -> str:
    """
    Advanced unified cleaner for training and inference:
    - Lowercase and basic cleanup
    - Remove URLs, emails, special characters
    - Remove extra whitespace
    - Lemmatize using spaCy if available
    - Remove stopwords
    - Return cleaned text with meaningful words only
    """
    text = str(text).lower()

    # Remove URLs and emails
    text = re.sub(r'http\S+|www\.\S+|[\w\.-]+@[\w\.-]+\.\w+', ' ', text)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Remove mentions and hashtags but keep content
    text = re.sub(r'@\w+|#', ' ', text)

    # Normalize numbers to <NUM> token (preserves sentence structure)
    # "scored in the 68th minute" → "scored in the NUM minute" (not broken gibberish)
    text = re.sub(r'\b\d+(?:[.,]\d+)*%?\b', ' NUM ', text)

    # Remove special characters and remaining digits (keep letters, spaces, hyphens, and NUM)
    # P2-3 FIX: was [^a-z\s\-] which stripped uppercase NUM inserted by line 48.
    text = re.sub(r"[^a-zA-Z\s\-]", " ", text)


    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if USE_SPACY and text:
        try:
            doc = nlp(text)
            # Lemmatize and filter
            tokens = [
                tok.lemma_ for tok in doc
                if not tok.is_stop and tok.is_alpha and tok.lemma_ not in ENHANCED_STOPWORDS
            ]
            return " ".join(tokens).strip()
        except Exception:
            pass

    # Fallback: remove common stopwords manually
    tokens = [word for word in text.split() if word not in ENHANCED_STOPWORDS and len(word) > 2]
    return " ".join(tokens).strip()

def extract_features(text: str) -> dict:
    """
    Extract linguistic features useful for fake news detection:
    - sentence count
    - average sentence length
    - question count
    - exclamation count
    - all caps word count
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    total_words = len(text.split())
    avg_sent_length = total_words / len(sentences) if sentences else 0

    question_count = text.count('?')
    exclamation_count = text.count('!')
    all_caps_words = len([w for w in text.split() if w.isupper() and len(w) > 1])

    return {
        'sentence_count': len(sentences),
        'avg_sentence_length': avg_sent_length,
        'question_count': question_count,
        'exclamation_count': exclamation_count,
        'all_caps_count': all_caps_words,
        'total_words': total_words
    }

def get_conspiracy_indicators(text: str) -> int:
    """
    Count conspiracy theory language indicators
    """
    conspiracy_keywords = [
        'cover up', 'hidden truth', 'secret', 'conspiracy', 'prove', 'liar',
        'government lies', 'fake news', 'mainstream media', 'deep state',
        'shadow government', 'illuminati', 'elite', 'new world order'
    ]

    text_lower = text.lower()
    count = sum(text_lower.count(keyword) for keyword in conspiracy_keywords)
    return count

def get_sensationalism_score(text: str) -> float:
    """
    Calculate sensationalism score based on language patterns
    """
    sensational_words = [
        'shocking', 'stunning', 'exclusive', 'breaking', 'unbelievable',
        'incredible', 'amazing', 'horrible', 'tragic', 'devastating',
        'bombshell', 'scandal', 'massive', 'huge', 'enormous'
    ]

    text_lower = text.lower()
    count = sum(text_lower.count(word) for word in sensational_words)
    total_words = len(text.split())

    return (count / total_words) if total_words > 0 else 0

def extract_keywords(text: str, max_keywords: int = 5) -> str:
    """Extract main keywords from text for searching (prefer capitalized entity-like tokens)"""
    cap_words = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text)
    if not cap_words:
        words = re.findall(r"\w{4,}", text)
        stop = {'that', 'this', 'from', 'with', 'have', 'about', 'would', 'could', 'should',
                'their', 'which', 'there', 'these', 'where', 'what', 'when', 'will', 'would'}
        words = [w for w in words if w.lower() not in stop]
        cap_words = words

    seen = set()
    keywords = []
    for w in cap_words:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            keywords.append(w)
        if len(keywords) >= max_keywords:
            break
    return ' '.join(keywords[:max_keywords])
