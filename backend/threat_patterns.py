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
