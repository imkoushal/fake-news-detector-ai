"""
Lightweight language/script detection for Indic text routing.
No external dependencies — uses Unicode range checks.
"""
import re


# Unicode block ranges for major Indic scripts
_DEVANAGARI = re.compile(r'[\u0900-\u097F]')   # Hindi, Marathi, Sanskrit
_BENGALI    = re.compile(r'[\u0980-\u09FF]')   # Bengali, Assamese
_GURMUKHI   = re.compile(r'[\u0A00-\u0A7F]')   # Punjabi
_GUJARATI   = re.compile(r'[\u0A80-\u0AFF]')   # Gujarati
_TAMIL      = re.compile(r'[\u0B80-\u0BFF]')   # Tamil
_TELUGU     = re.compile(r'[\u0C00-\u0C7F]')   # Telugu
_KANNADA    = re.compile(r'[\u0C80-\u0CFF]')   # Kannada
_MALAYALAM  = re.compile(r'[\u0D00-\u0D7F]')   # Malayalam
_ARABIC     = re.compile(r'[\u0600-\u06FF]')   # Urdu (Nastaliq)

# Common Hinglish patterns: Hindi words written in Latin script
_HINGLISH_WORDS = re.compile(
    r'\b(kya|hai|nahi|yeh|woh|aap|hum|tum|kar|karo|karna|dekho|bhai|'
    r'bhai|accha|theek|sach|jhooth|jhuth|khabar|paisa|rupee|lakh|crore|'
    r'sarkar|sarkari|yojana|pradhan|mantri|modi|bjp|congress|aam|aadmi|'
    r'whatsapp|forwarded|aaj|kal|bahut|bohot|bada|chota|kuch|sabhi|log|'
    r'desh|bharat|india|hindu|muslim|masjid|mandir|gau|raksha)\b',
    re.IGNORECASE
)


def detect_language(text: str) -> dict:
    """Detect the dominant script/language of the input text.
    
    Returns:
        {
            "script": "devanagari" | "bengali" | ... | "latin" | "mixed",
            "lang": "hi" | "bn" | ... | "en" | "hinglish",
            "indic_ratio": float,   # fraction of Indic chars
            "is_indic": bool,       # True if primarily Indic text
        }
    """
    if not text or len(text.strip()) < 5:
        return {"script": "latin", "lang": "en", "indic_ratio": 0.0, "is_indic": False}
    
    alpha_chars = re.sub(r'[\s\d\W]', '', text)
    total = max(len(alpha_chars), 1)
    
    # Count characters per script
    counts = {
        "devanagari": len(_DEVANAGARI.findall(text)),
        "bengali":    len(_BENGALI.findall(text)),
        "gurmukhi":   len(_GURMUKHI.findall(text)),
        "gujarati":   len(_GUJARATI.findall(text)),
        "tamil":      len(_TAMIL.findall(text)),
        "telugu":     len(_TELUGU.findall(text)),
        "kannada":    len(_KANNADA.findall(text)),
        "malayalam":  len(_MALAYALAM.findall(text)),
        "arabic":     len(_ARABIC.findall(text)),
    }
    
    indic_total = sum(counts.values())
    indic_ratio = indic_total / total
    
    # Script-to-language mapping
    script_lang = {
        "devanagari": "hi", "bengali": "bn", "gurmukhi": "pa",
        "gujarati": "gu", "tamil": "ta", "telugu": "te",
        "kannada": "kn", "malayalam": "ml", "arabic": "ur",
    }
    
    # If ≥15% Indic characters, it's Indic text
    if indic_ratio >= 0.15:
        dominant = max(counts, key=counts.get)
        return {
            "script": dominant,
            "lang": script_lang.get(dominant, "hi"),
            "indic_ratio": round(indic_ratio, 3),
            "is_indic": True,
        }
    
    # Check for Hinglish (Hindi words in Latin script)
    hinglish_matches = _HINGLISH_WORDS.findall(text)
    words = text.split()
    hinglish_ratio = len(hinglish_matches) / max(len(words), 1)
    
    if hinglish_ratio >= 0.15:
        return {
            "script": "latin",
            "lang": "hinglish",
            "indic_ratio": round(hinglish_ratio, 3),
            "is_indic": True,
        }
    
    return {"script": "latin", "lang": "en", "indic_ratio": 0.0, "is_indic": False}


def needs_indic_routing(text: str) -> bool:
    """Quick check: should this text bypass the English ML model?"""
    return detect_language(text)["is_indic"]
