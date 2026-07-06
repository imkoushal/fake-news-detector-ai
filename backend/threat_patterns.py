"""
India Threat Patterns ÔÇö Enterprise Module
9-category scam/misinformation detection engine with 150+ India-specific keywords.
"""

INDIA_THREAT_PATTERNS = {
    "upi_banking_fraud": {
        "label": "­ƒÅª UPI / Banking Fraud",
        "weight": 3,
        "keywords": [
            "upi", "paytm", "phonepe", "google pay", "gpay", "bhim",
            "otp", "share otp", "enter otp", "send otp", "otp number",
            "bank account", "account blocked", "account suspended",
            "kyc update", "kyc expired", "pan card link", "aadhaar link",
            "sbi", "hdfc", "icici", "pnb", "rbi", "reserve bank",
            "credit card block", "debit card block", "atm pin",
            "rupees credited", "lakhs credited", "transfer failed",
            "click here to verify", "verify your account",
        ],
    },
    "fake_govt_scheme": {
        "label": "­ƒÅø´©Å Fake Government Scheme",
        "weight": 3,
        "keywords": [
            "pm kisan", "pm modi", "pradhan mantri", "free ration",
            "free laptop", "free mobile", "free gas cylinder",
            "government giving", "sarkari yojana", "jan dhan",
            "ayushman bharat", "mudra loan", "apply now",
            "registration link", "last date to apply",
            "rs 6000", "Ôé╣6000", "Ôé╣15000", "rs 15000",
            "ration card", "apl bpl", "central government announced",
            "state government announced", "subsidy", "scholarship",
        ],
    },
    "whatsapp_forward": {
        "label": "­ƒô▒ WhatsApp Forward Pattern",
        "weight": 2,
        "keywords": [
            "forward this", "share this", "send to 10", "send to all",
            "forward to everyone", "share in all groups", "must read",
            "please share", "please forward", "viral", "going viral",
            "before they delete", "before it gets removed",
            "deleted from internet", "banned from sharing",
            "as received", "forwarded as received", "copy paste",
            "broadcast", "important message", "urgent message",
        ],
    },
    "health_misinfo": {
        "label": "­ƒÆè Health Misinformation",
        "weight": 3,
        "keywords": [
            "miracle cure", "guaranteed cure", "home remedy",
            "doctors don't want", "big pharma", "natural cure",
            "corona cure", "covid cure", "dengue cure",
            "drink hot water", "boil neem leaves", "cow urine",
            "gaumutra", "immunity booster", "ayurvedic cure for",
            "unani cure", "siddha medicine", "homeopathy cure",
            "vaccine dangerous", "vaccine kills", "5g corona",
            "microchip vaccine", "bill gates vaccine",
            "magnetic vaccine", "vaccine side effects death",
        ],
    },
    "communal_trigger": {
        "label": "ÔÜá´©Å Communal / Hate Trigger",
        "weight": 4,
        "keywords": [
            "love jihad", "land jihad", "population jihad",
            "hindu khatre mein", "sanatan danger", "anti-national",
            "urban naxal", "tukde tukde", "converted",
            "forced conversion", "rice bag", "demolish temple",
            "cow slaughter", "beef ban", "mob lynching",
            "stone pelting", "communal riot", "religious war",
        ],
    },
    "fake_job_scam": {
        "label": "­ƒÆ╝ Fake Job / Recruitment",
        "weight": 2,
        "keywords": [
            "upsc vacancy", "railway vacancy", "ssc vacancy",
            "government job", "sarkari naukri", "walk-in interview",
            "no experience needed", "work from home earn",
            "earn lakhs", "earn thousands daily", "part time job",
            "data entry job", "typing job", "registration fee",
            "pay to join", "guaranteed placement", "100% job guarantee",
        ],
    },
    "religious_manipulation": {
        "label": "­ƒòë´©Å Religious Manipulation",
        "weight": 2,
        "keywords": [
            "temple miracle", "mosque miracle", "church miracle",
            "god appeared", "divine message", "prophecy fulfilled",
            "end of world", "qayamat", "kaliyuga ending",
            "angel appeared", "seen in clouds", "water turning",
            "statue drinking milk", "ganpati drinking milk",
        ],
    },
    "conspiracy_india": {
        "label": "­ƒö« India-Specific Conspiracy",
        "weight": 2,
        "keywords": [
            "isi agent", "china attack", "pakistan attack",
            "border breach", "surgical strike", "war declared",
            "army alert", "martial law", "emergency declared",
            "internet shutdown", "curfew imposed", "shoot at sight",
            "foreign funded", "soros funded", "cia funded",
            "raw agent", "deep state india",
        ],
    },
    "fake_reward_lottery": {
        "label": "­ƒÄ░ Fake Reward / Lottery",
        "weight": 3,
        "keywords": [
            "lottery winner", "you have won", "congratulations you won",
            "claim your prize", "lucky draw", "jio lottery",
            "whatsapp lottery", "amazon lucky draw", "flipkart winner",
            "free iphone", "free recharge", "free data",
            "scratch card", "spin the wheel", "cashback offer",
            "claim now", "limited time offer", "offer expires",
        ],
    },
}


# ── Phase 10.2: Hinglish + Devanagari expansion ──────────────────────────────
# The base keywords above are English-only, but the target audience (Indian
# WhatsApp/Telegram users) writes in romanized Hindi ("Hinglish") and Devanagari.
# We MERGE extra keywords into the categories above instead of editing them, so
# the base list stays intact and the two scripts are reviewable in one place.
#
# False-positive discipline:
#   • Romanized terms are multi-word phrases ("otp bhejo", not "otp") so they
#     can't collide with substrings of unrelated English words
#     (e.g. "sena" inside "arsenal", "muft" inside "mufti").
#   • Devanagari terms share no bytes with ASCII, so single words are safe.
# scan_india_threats lowercases input; .lower() is a no-op on Devanagari and
# substring matching works identically for both scripts.
_HINGLISH_EXPANSION = {
    "upi_banking_fraud": [
        "otp bataye", "otp bhejo", "otp share karo", "otp batao",
        "khata band", "khata block", "account band ho",
        "kyc update karo", "kyc karwaye", "turant transfer",
        "paisa transfer karo", "link par click karo", "bank se call",
        "ओटीपी", "खाता बंद", "केवाईसी", "यूपीआई", "लिंक पर क्लिक",
    ],
    "fake_govt_scheme": [
        "sarkari yojana", "yojana ka labh", "muft me", "abhi apply karo",
        "aakhri tarikh", "antim tithi", "labharthi list", "panjikaran karo",
        "सरकारी योजना", "मुफ्त", "मुफ़्त", "पंजीकरण", "आवेदन करें",
        "अंतिम तिथि", "लाभार्थी",
    ],
    "whatsapp_forward": [
        "sabko bhejo", "sabko forward karo", "har group me bhejo",
        "delete hone se pehle", "jaldi share karo", "zaroor share kare",
        "aage bhejo", "sabko batao",
        "सभी को भेजें", "शेयर करें", "फॉरवर्ड करें", "जरूर भेजें",
        "आगे भेजें", "वायरल",
    ],
    "health_misinfo": [
        "ramban ilaj", "gharelu nuskha", "desi ilaj", "chamatkari ilaj",
        "corona ka ilaj", "bina dawa theek", "immunity badhaye",
        "रामबाण इलाज", "घरेलू नुस्खा", "चमत्कारी इलाज", "कोरोना का इलाज",
        "गौमूत्र", "देसी इलाज",
    ],
    "communal_trigger": [
        "hindu khatre mein hai", "dharm khatre mein", "dharmantaran",
        "gau hatya", "jabran dharmantaran",
        "हिंदू खतरे में", "धर्म खतरे में", "धर्मांतरण", "गौ हत्या",
    ],
    "fake_job_scam": [
        "sarkari naukri", "ghar baithe kamaye", "ghar baithe kaam",
        "roz kamaye", "part time kaam", "registration fees jama",
        "naukri pakki", "paise jama karo",
        "सरकारी नौकरी", "घर बैठे कमाएं", "पंजीकरण शुल्क", "रोज कमाएं",
    ],
    "religious_manipulation": [
        "bhagwan ka sandesh", "mandir me chamatkar", "doodh pi raha",
        "duniya ka ant", "murti doodh pi",
        "चमत्कार", "भगवान का संदेश", "दूध पी रही", "प्रलय", "कयामत",
    ],
    "conspiracy_india": [
        "yudh shuru", "jang ka elan", "curfew laga", "internet band kiya",
        "sena alert par", "seema par hamla",
        "युद्ध शुरू", "कर्फ्यू", "इंटरनेट बंद", "सेना अलर्ट", "सीमा पर हमला",
    ],
    "fake_reward_lottery": [
        "aap jeet gaye", "inaam jeeta", "lucky draw jeeta",
        "muft recharge", "muft mobile", "inaam claim karo", "badhai ho aap",
        "आप जीत गए", "इनाम", "लकी ड्रा", "बधाई हो", "मुफ्त रिचार्ज", "पुरस्कार",
    ],
}

for _cat, _extra_kws in _HINGLISH_EXPANSION.items():
    if _cat in INDIA_THREAT_PATTERNS:
        INDIA_THREAT_PATTERNS[_cat]["keywords"].extend(_extra_kws)


def scan_india_threats(text: str) -> dict:
    """Scan text for India-specific misinformation and scam patterns."""
    text_lower = text.lower()
    detections = []
    total_score = 0
    max_possible = 0

    for pattern_id, pattern in INDIA_THREAT_PATTERNS.items():
        hits = [kw for kw in pattern["keywords"] if kw in text_lower]
        weight = pattern["weight"]
        max_possible += weight * 5

        if hits:
            cat_score = min(len(hits) * weight * 5, 100)
            total_score += cat_score
            detections.append({
                "category": pattern_id,
                "label": pattern["label"],
                "severity": "critical" if cat_score >= 40 else "warning" if cat_score >= 15 else "info",
                "matched_keywords": hits[:8],
                "match_count": len(hits),
                "score": cat_score,
            })

    risk_score = min(round(total_score / max(max_possible, 1) * 100), 100) if detections else 0

    if risk_score >= 60:
        risk_level = "critical"
        advisory = "ÔÜá´©Å HIGH RISK ÔÇö This content matches multiple known Indian scam/misinformation patterns. Do NOT share, click links, or provide personal information."
    elif risk_score >= 30:
        risk_level = "elevated"
        advisory = "­ƒƒí ELEVATED RISK ÔÇö Some suspicious patterns detected. Verify claims from official sources (PIB, IANS) before sharing."
    elif risk_score >= 10:
        risk_level = "low"
        advisory = "­ƒƒó LOW RISK ÔÇö Minor pattern matches detected. Exercise normal caution."
    else:
        risk_level = "safe"
        advisory = "Ô£à No known Indian scam or misinformation patterns detected."

    detections.sort(key=lambda x: x["score"], reverse=True)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "advisory": advisory,
        "threats_found": len(detections),
        "detections": detections,
        "patterns_scanned": len(INDIA_THREAT_PATTERNS),
    }
