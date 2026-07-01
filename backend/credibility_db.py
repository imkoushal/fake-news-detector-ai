"""
Source Credibility Database ÔÇö Enterprise Module
Domain reputation system covering 80+ Indian and international news sources.
Each entry: (credibility_score, category, bias, description)
"""

SOURCE_CREDIBILITY_DB = {
    # ÔöÇÔöÇ TIER 1: Gold-Standard Wire Services & Fact-Checkers (95-100) ÔöÇÔöÇ
    "reuters.com":       (98, "wire_service", "center", "Global wire service, gold standard"),
    "apnews.com":        (98, "wire_service", "center", "Associated Press ÔÇö US wire service"),
    "afp.com":           (97, "wire_service", "center", "Agence France-Presse ÔÇö French wire service"),
    "pib.gov.in":        (96, "government", "center", "Press Information Bureau ÔÇö Indian govt"),
    "ians.in":           (95, "wire_service", "center", "Indo-Asian News Service"),
    "ptinews.com":       (95, "wire_service", "center", "Press Trust of India"),
    "uni.in":            (93, "wire_service", "center", "United News of India"),

    # ÔöÇÔöÇ Indian Fact-Checkers (92-96) ÔöÇÔöÇ
    "altnews.in":        (96, "fact_checker", "center", "Alt News ÔÇö Indian fact-checker"),
    "boomlive.in":       (95, "fact_checker", "center", "BOOM Live ÔÇö Indian fact-checker"),
    "factchecker.in":    (94, "fact_checker", "center", "FactChecker.in"),
    "vishvasnews.com":   (93, "fact_checker", "center", "Vishvas News ÔÇö Hindi fact-checker"),
    "thequint.com":      (88, "fact_checker", "center-left", "The Quint ÔÇö Webqoof fact-check"),
    "factly.in":         (93, "fact_checker", "center", "Factly ÔÇö data-driven fact-checker"),
    "newschecker.in":    (91, "fact_checker", "center", "Newschecker India"),

    # ÔöÇÔöÇ International Fact-Checkers (92-96) ÔöÇÔöÇ
    "snopes.com":        (95, "fact_checker", "center", "Snopes ÔÇö oldest fact-checker"),
    "politifact.com":    (94, "fact_checker", "center", "PolitiFact ÔÇö political fact-checks"),
    "factcheck.org":     (95, "fact_checker", "center", "FactCheck.org ÔÇö Annenberg"),
    "fullfact.org":      (94, "fact_checker", "center", "Full Fact ÔÇö UK fact-checker"),

    # ÔöÇÔöÇ TIER 2: Major Indian Newspapers & Broadcasters (80-92) ÔöÇÔöÇ
    "thehindu.com":      (92, "newspaper", "center-left", "The Hindu ÔÇö national daily"),
    "indianexpress.com": (90, "newspaper", "center", "Indian Express ÔÇö national daily"),
    "livemint.com":      (89, "newspaper", "center", "Mint ÔÇö business/finance"),
    "ndtv.com":          (87, "broadcaster", "center-left", "NDTV ÔÇö national broadcaster"),
    "hindustantimes.com":(86, "newspaper", "center", "Hindustan Times ÔÇö national daily"),
    "timesofindia.indiatimes.com": (84, "newspaper", "center", "Times of India"),
    "economictimes.indiatimes.com": (85, "newspaper", "center", "Economic Times"),
    "business-standard.com": (88, "newspaper", "center", "Business Standard"),
    "deccanherald.com":  (86, "newspaper", "center", "Deccan Herald"),
    "telegraphindia.com":(85, "newspaper", "center-left", "The Telegraph India"),
    "scroll.in":         (84, "digital_media", "center-left", "Scroll.in"),
    "thewire.in":        (83, "digital_media", "center-left", "The Wire"),
    "newslaundry.com":   (82, "digital_media", "center-left", "Newslaundry"),
    "theprint.in":       (85, "digital_media", "center", "The Print"),
    "firstpost.com":     (82, "digital_media", "center-right", "Firstpost"),
    "news18.com":        (80, "broadcaster", "center-right", "News18"),
    "aajtak.in":         (78, "broadcaster", "center", "Aaj Tak ÔÇö Hindi news"),
    "abplive.com":       (77, "broadcaster", "center", "ABP Live"),
    "zee5.com":          (76, "broadcaster", "center-right", "Zee News"),
    "republic.in":       (72, "broadcaster", "right", "Republic TV"),
    "opindia.com":       (65, "digital_media", "right", "OpIndia ÔÇö opinion-heavy"),
    "swarajyamag.com":   (68, "digital_media", "right", "Swarajya Magazine"),
    "thefederal.com":    (80, "digital_media", "center", "The Federal"),
    "southfirst.com":    (79, "digital_media", "center", "South First"),

    # ÔöÇÔöÇ TIER 2: Major International (82-95) ÔöÇÔöÇ
    "bbc.com":           (93, "broadcaster", "center", "BBC ÔÇö British broadcaster"),
    "bbc.co.uk":         (93, "broadcaster", "center", "BBC UK"),
    "nytimes.com":       (91, "newspaper", "center-left", "New York Times"),
    "washingtonpost.com":(90, "newspaper", "center-left", "Washington Post"),
    "theguardian.com":   (89, "newspaper", "center-left", "The Guardian"),
    "wsj.com":           (90, "newspaper", "center-right", "Wall Street Journal"),
    "ft.com":            (91, "newspaper", "center", "Financial Times"),
    "economist.com":     (92, "newspaper", "center", "The Economist"),
    "bloomberg.com":     (90, "newspaper", "center", "Bloomberg"),
    "npr.org":           (89, "broadcaster", "center", "NPR ÔÇö US public radio"),
    "pbs.org":           (89, "broadcaster", "center", "PBS ÔÇö US public TV"),
    "cnn.com":           (82, "broadcaster", "center-left", "CNN"),
    "nbcnews.com":       (83, "broadcaster", "center-left", "NBC News"),
    "cbsnews.com":       (84, "broadcaster", "center", "CBS News"),
    "abcnews.go.com":    (83, "broadcaster", "center", "ABC News"),
    "usatoday.com":      (82, "newspaper", "center", "USA Today"),
    "aljazeera.com":     (83, "broadcaster", "center", "Al Jazeera"),
    "dw.com":            (85, "broadcaster", "center", "Deutsche Welle"),
    "france24.com":      (84, "broadcaster", "center", "France 24"),

    # ÔöÇÔöÇ Academic & Research (90-96) ÔöÇÔöÇ
    "nature.com":        (96, "academic", "center", "Nature ÔÇö scientific journal"),
    "science.org":       (96, "academic", "center", "Science Magazine"),
    "thelancet.com":     (95, "academic", "center", "The Lancet ÔÇö medical journal"),
    "who.int":           (94, "government", "center", "World Health Organization"),
    "nih.gov":           (94, "government", "center", "US National Institutes of Health"),
    "icmr.gov.in":       (93, "government", "center", "Indian Council of Medical Research"),
    "mohfw.gov.in":      (93, "government", "center", "Indian Ministry of Health"),

    # ÔöÇÔöÇ TIER 3: Known Unreliable / Misinformation (5-30) ÔöÇÔöÇ
    "infowars.com":      (5,  "conspiracy", "far-right", "Infowars ÔÇö conspiracy site"),
    "naturalnews.com":   (8,  "conspiracy", "far-right", "Natural News ÔÇö health misinfo"),
    "beforeitsnews.com": (10, "conspiracy", "far-right", "Before It's News ÔÇö unverified"),
    "yournewswire.com":  (8,  "conspiracy", "far-right", "Your News Wire ÔÇö fake news"),
    "worldnewsdailyreport.com": (5, "satire", "none", "WDNR ÔÇö satire/fake"),
    "theonion.com":      (15, "satire", "center", "The Onion ÔÇö satire (not real news)"),
    "clickhole.com":     (15, "satire", "center", "ClickHole ÔÇö satire"),
    "empirenews.net":    (5,  "fake", "none", "Empire News ÔÇö entirely fabricated"),
    "newsbreakhere.com": (8,  "fake", "none", "Fake news generator site"),
    "thenewsguards.com": (10, "fake", "none", "Impersonation of NewsGuard"),
    "postcard.news":     (25, "misleading", "right", "Postcard News ÔÇö frequent misinfo"),
    "kreately.in":       (30, "opinion", "right", "Kreately ÔÇö opinion as news"),
}
