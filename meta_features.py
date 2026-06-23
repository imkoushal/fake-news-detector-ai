"""
Meta-Feature Extractor for Fake News Detection

Phase 2: Handcrafted linguistic features that capture signals TF-IDF misses.
These features are computed on RAW text (before clean_text) because cleaning
destroys the very signals we want to detect (caps, punctuation, URLs, etc.).

Features computed (20 total):
  - Structural: sentence_count, avg_sentence_length, word_count
  - Punctuation: exclamation_ratio, question_ratio
  - Caps: all_caps_ratio, title_case_ratio, caps_char_ratio
  - Vocabulary: lexical_diversity, avg_word_length
  - Style: first_person_ratio, quoted_source_count, number_count, url_count
  - Red flags: conspiracy_score, sensationalism_score, red_flag_score
  - Readability: flesch_kincaid_grade
  - Attribution: has_attribution, passive_voice_ratio
  - Clickbait: clickbait_score
"""

import re
import numpy as np
from typing import List


# ─── Keyword lists (frozen for consistency) ───

CONSPIRACY_KEYWORDS = [
    'cover up', 'hidden truth', 'secret', 'conspiracy', 'prove', 'liar',
    'government lies', 'fake news', 'mainstream media', 'deep state',
    'shadow government', 'illuminati', 'elite', 'new world order',
    'big pharma', 'wake up', 'sheeple', 'they don\'t want you',
]

SENSATIONAL_WORDS = [
    'shocking', 'stunning', 'exclusive', 'breaking', 'unbelievable',
    'incredible', 'amazing', 'horrible', 'tragic', 'devastating',
    'bombshell', 'scandal', 'massive', 'huge', 'enormous',
    'outrageous', 'explosive', 'insane', 'terrifying', 'unprecedented',
]

CLICKBAIT_PATTERNS = [
    r"you won'?t believe",
    r"this one (?:weird|simple) trick",
    r"doctors (?:don'?t want you to know|hate)",
    r"what happened next",
    r"share before (?:it'?s )?deleted",
    r"click here|tap here",
    r"the truth about",
    r"exposed|revealed",
    r"\d+ (?:reasons|things|ways|facts)",
    r"what .* don'?t want you to know",
]

ATTRIBUTION_PATTERNS = [
    r'according to', r'researchers (?:say|found|suggest)',
    r'studies? (?:show|suggest|indicate|found)',
    r'scientists? (?:say|found|suggest|believe)',
    r'the (?:report|study|analysis) (?:found|shows|indicates)',
    r'experts? (?:say|warn|believe|suggest)',
    r'officials? (?:say|said|confirmed|announced)',
]

FIRST_PERSON_PRONOUNS = {'i', 'me', 'my', 'mine', 'myself', 'we', 'us', 'our', 'ours', 'ourselves'}

PASSIVE_MARKERS = [
    r'\b(?:is|was|were|are|been|being|be)\s+(?:\w+ly\s+)?(?:\w+ed|known|seen|found|made|given|taken|done|said|told)\b',
]


# ─── Feature names (order must match extract_single) ───

FEATURE_NAMES = [
    'sentence_count',
    'avg_sentence_length',
    'word_count',
    'exclamation_ratio',
    'question_ratio',
    'all_caps_ratio',
    'title_case_ratio',
    'caps_char_ratio',
    'lexical_diversity',
    'avg_word_length',
    'first_person_ratio',
    'quoted_source_count',
    'number_count',
    'url_count',
    'conspiracy_score',
    'sensationalism_score',
    'red_flag_score',
    'flesch_kincaid_grade',
    'has_attribution',
    'clickbait_score',
]

N_META_FEATURES = len(FEATURE_NAMES)


def extract_single(text: str) -> np.ndarray:
    """
    Extract meta features from a single raw text string.
    Returns a 1D numpy array of shape (N_META_FEATURES,).

    IMPORTANT: Pass the ORIGINAL text, not the cleaned text.
    """
    text = str(text)
    text_lower = text.lower()
    words = text.split()
    n_words = max(len(words), 1)
    words_lower = [w.lower() for w in words]

    # --- Structural ---
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    n_sentences = max(len(sentences), 1)
    avg_sent_len = n_words / n_sentences

    # --- Punctuation ratios (per word) ---
    excl_ratio = text.count('!') / n_words
    ques_ratio = text.count('?') / n_words

    # --- Caps features ---
    all_caps_words = sum(1 for w in words if w.isupper() and len(w) > 1)
    all_caps_ratio = all_caps_words / n_words

    title_case_words = sum(1 for w in words if w.istitle() and len(w) > 1)
    title_case_ratio = title_case_words / n_words

    alpha_chars = [c for c in text if c.isalpha()]
    n_alpha = max(len(alpha_chars), 1)
    caps_char_ratio = sum(1 for c in alpha_chars if c.isupper()) / n_alpha

    # --- Vocabulary ---
    unique_words = set(words_lower)
    lexical_diversity = len(unique_words) / n_words

    word_lengths = [len(w) for w in words]
    avg_word_length = sum(word_lengths) / n_words

    # --- Style ---
    first_person_count = sum(1 for w in words_lower if w in FIRST_PERSON_PRONOUNS)
    first_person_ratio = first_person_count / n_words

    # Count quoted sources (pairs of quotes)
    quoted_source_count = text.count('"') // 2 + text.count('\u201c')  # straight + curly quotes

    # Count numbers / statistics
    number_count = len(re.findall(r'\b\d+(?:\.\d+)?%?\b', text))

    # Count URLs
    url_count = len(re.findall(r'https?://\S+|www\.\S+', text))

    # --- Red flag signals ---
    conspiracy_score = sum(text_lower.count(kw) for kw in CONSPIRACY_KEYWORDS) / n_words
    sensationalism_score = sum(text_lower.count(w) for w in SENSATIONAL_WORDS) / n_words

    # Red flag patterns
    red_flags = 0.0
    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, text_lower):
            red_flags += 1.0
    if text.count('!') > 3:
        red_flags += 0.5
    if text.count('?') > 5:
        red_flags += 0.5
    red_flag_score = min(red_flags, 10.0) / 10.0

    # --- Readability (Flesch-Kincaid grade level) ---
    syllables = sum(1 for c in text_lower if c in 'aeiou')
    avg_syl = syllables / n_words
    fk_grade = max(0, min(18, 0.39 * avg_sent_len + 11.8 * avg_syl - 15.59))

    # --- Attribution ---
    has_attribution = 0.0
    for pattern in ATTRIBUTION_PATTERNS:
        if re.search(pattern, text_lower):
            has_attribution = 1.0
            break

    # --- Clickbait score ---
    clickbait_hits = sum(1 for p in CLICKBAIT_PATTERNS if re.search(p, text_lower))
    clickbait_score = min(clickbait_hits, 5) / 5.0

    return np.array([
        n_sentences,           # sentence_count
        avg_sent_len,          # avg_sentence_length
        n_words,               # word_count
        excl_ratio,            # exclamation_ratio
        ques_ratio,            # question_ratio
        all_caps_ratio,        # all_caps_ratio
        title_case_ratio,      # title_case_ratio
        caps_char_ratio,       # caps_char_ratio
        lexical_diversity,     # lexical_diversity
        avg_word_length,       # avg_word_length
        first_person_ratio,    # first_person_ratio
        quoted_source_count,   # quoted_source_count
        number_count,          # number_count
        url_count,             # url_count
        conspiracy_score,      # conspiracy_score
        sensationalism_score,  # sensationalism_score
        red_flag_score,        # red_flag_score
        fk_grade,              # flesch_kincaid_grade
        has_attribution,       # has_attribution
        clickbait_score,       # clickbait_score
    ], dtype=np.float64)


def extract_batch(texts: List[str]) -> np.ndarray:
    """
    Extract meta features from a batch of texts.
    Returns a 2D numpy array of shape (n_texts, N_META_FEATURES).
    """
    return np.vstack([extract_single(t) for t in texts])
