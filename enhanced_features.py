"""
Enhanced features module for fake news detection
"""
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

# Known trusted sources
TRUSTED_SOURCES = [
    'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk',
    'nytimes.com', 'washingtonpost.com', 'theguardian.com',
    'bloomberg.com', 'wsj.com', 'ft.com', 'economist.com',
    'npr.org', 'pbs.org', 'cnn.com', 'abcnews.go.com',
    'cbsnews.com', 'nbcnews.com', 'usatoday.com', 'latimes.com'
]

# Known unreliable sources
UNRELIABLE_SOURCES = [
    'infowars.com', 'naturalnews.com', 'beforeitsnews.com',
    'yournewswire.com', 'theonion.com', 'clickhole.com'
]

# Topic keywords
TOPIC_KEYWORDS = {
    'politics': ['election', 'president', 'congress', 'senate', 'democrat', 'republican', 'vote', 'policy', 'government'],
    'health': ['health', 'medical', 'doctor', 'disease', 'vaccine', 'treatment', 'cure', 'hospital', 'patient'],
    'technology': ['technology', 'tech', 'software', 'hardware', 'ai', 'artificial intelligence', 'computer', 'internet', 'digital'],
    'science': ['science', 'research', 'study', 'scientist', 'experiment', 'discovery', 'laboratory'],
    'business': ['business', 'economy', 'stock', 'market', 'trade', 'company', 'corporate', 'finance'],
    'entertainment': ['movie', 'music', 'celebrity', 'film', 'actor', 'singer', 'entertainment']
}

def extract_domain(text: str) -> str:
    """Extract domain from URL in text"""
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    if urls:
        parsed = urlparse(urls[0])
        return parsed.netloc.replace('www.', '')
    return None

def analyze_source(domain: str) -> Dict:
    """Analyze source credibility"""
    if not domain:
        return {'credible': False, 'reputation': 50, 'category': 'unknown'}

    domain = domain.lower()

    if any(trusted in domain for trusted in TRUSTED_SOURCES):
        return {'credible': True, 'reputation': 95, 'category': 'trusted'}
    elif any(unreliable in domain for unreliable in UNRELIABLE_SOURCES):
        return {'credible': False, 'reputation': 10, 'category': 'unreliable'}
    else:
        return {'credible': False, 'reputation': 50, 'category': 'unknown'}

def classify_topic(text: str) -> Tuple[str, float]:
    """Classify article topic"""
    text_lower = text.lower()
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        scores[topic] = score

    if not scores or max(scores.values()) == 0:
        return 'general', 0.0

    best_topic = max(scores, key=scores.get)
    confidence = scores[best_topic] / sum(scores.values())

    return best_topic, confidence

def get_word_importance(text: str, vectorizer, model, top_n: int = 20) -> List[Tuple[str, float]]:
    """Get most important words for classification"""

    # Transform text
    features = vectorizer.transform([text])

    # Get feature names
    feature_names = vectorizer.get_feature_names_out()

    # Get non-zero features
    nonzero_indices = features.nonzero()[1]
    scores = features.data

    # Sort by score
    word_scores = [(feature_names[idx], scores[i]) for i, idx in enumerate(nonzero_indices)]
    word_scores.sort(key=lambda x: x[1], reverse=True)

    return word_scores[:top_n]

def get_model_predictions(model, text_features) -> Dict:
    """Get individual predictions from each model in ensemble"""
    predictions = {}

    if hasattr(model, 'estimators_'):
        for i, estimator in enumerate(model.estimators_):
            try:
                pred = estimator.predict(text_features)[0]
                proba = estimator.predict_proba(text_features)[0] if hasattr(estimator, 'predict_proba') else [0.5, 0.5]
                predictions[f'Model_{i+1}'] = {
                    'prediction': 'REAL' if pred == 1 else 'FAKE',
                    'confidence': max(proba) * 100
                }
            except Exception:
                pass

    return predictions

def highlight_suspicious_phrases(text: str) -> List[Dict]:
    """Identify and highlight suspicious phrases in text"""
    suspicious_patterns = [
        (r'\b(doctors don\'t want you to know|they don\'t want you to know)\b', 'Medical Misinformation', 'high'),
        (r'\b(this one weird trick|one simple trick)\b', 'Clickbait', 'high'),
        (r'\b(big pharma|mainstream media|deep state)\b', 'Conspiracy Theory', 'medium'),
        (r'\b(share before (it\'s |this is )?deleted|share now)\b', 'Urgency Manipulation', 'high'),
        (r'\b(shocking|breaking|exposed|revealed)\b', 'Sensationalism', 'low'),
        (r'\b(miracle cure|ancient remedy|secret ingredient)\b', 'Medical Fraud', 'high'),
        (r'[A-Z]{5,}', 'Excessive Caps', 'low'),
        (r'!{3,}', 'Excessive Punctuation', 'low'),
    ]

    findings = []
    for pattern, category, severity in suspicious_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                'text': match.group(),
                'category': category,
                'severity': severity,
                'position': match.start()
            })

    return findings

def calculate_readability_score(text: str) -> Dict:
    """Calculate readability metrics"""
    sentences = text.count('.') + text.count('!') + text.count('?')
    words = len(text.split())

    if sentences == 0 or words == 0:
        return {'grade_level': 0, 'difficulty': 'Unknown'}

    avg_sentence_length = words / sentences

    # Simple readability score (Flesch-Kincaid approximation)
    syllables = sum(1 for char in text if char.lower() in 'aeiou')
    avg_syllables_per_word = syllables / words if words > 0 else 0

    grade_level = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
    grade_level = max(0, min(18, grade_level))  # Clamp between 0 and 18

    if grade_level < 6:
        difficulty = 'Very Easy'
    elif grade_level < 9:
        difficulty = 'Easy'
    elif grade_level < 12:
        difficulty = 'Moderate'
    elif grade_level < 16:
        difficulty = 'Difficult'
    else:
        difficulty = 'Very Difficult'

    return {
        'grade_level': round(grade_level, 1),
        'difficulty': difficulty,
        'avg_sentence_length': round(avg_sentence_length, 1),
        'word_count': words
    }

def extract_time_references(text: str) -> List[str]:
    """Extract time/date references from text"""
    time_patterns = [
        r'\b(yesterday|today|tomorrow)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b(last|this|next)\s+(week|month|year)\b'
    ]

    references = []
    for pattern in time_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        references.extend(matches)

    return references

def detect_fake_news_red_flags(text: str) -> float:
    """Detect obvious fake news indicators that override model prediction"""
    text_lower = text.lower()
    red_flags = 0
    max_red_flags = 10

    # Red flag patterns for obvious misinformation
    red_flag_patterns = [
        (r'doctors don\'t want you to know', 1),  # Medical misinformation
        (r'this one weird trick', 1),  # Clickbait
        (r'doctors hate|doctors are hiding', 1),  # Medical conspiracy
        (r'big pharma doesn\'t want', 1),  # Big pharma conspiracy
        (r'\bshare before (it\'s )?deleted', 1),  # Censorship claim
        (r'you won\'t believe what happened', 0.5),  # Clickbait
        (r'click here|tap here', 0.5),  # Suspicious links
        (r'unbelievable what .* did', 0.5),  # Sensationalism
        (r'the (government|elite|illuminati|deep state) (is|are) (hiding|covering)', 1),  # Conspiracy
        (r'ancient (remedy|secret|cure)', 0.8),  # Medical fraud
    ]

    for pattern, weight in red_flag_patterns:
        if re.search(pattern, text_lower):
            red_flags += weight

    # Count excessive sensational punctuation
    exclamations = text.count('!')
    questions = text.count('?')
    if exclamations > 3 or questions > 5:
        red_flags += 0.5

    # Check for unsubstantiated claims
    if re.search(r'(allegedly|reportedly|apparently|supposedly|claim[s]?).*?(found|discovered|revealed)', text_lower):
        if not re.search(r'(according to|researchers|scientists|studies)', text_lower):
            red_flags += 0.5

    return min(red_flags, max_red_flags) / max_red_flags  # Normalize to 0-1
