import requests
import streamlit as st
# Note: Gemini/google-generativeai removed — AI verification now handled
# via Groq REST API in api.py. This client only handles GNews searches.

def gemini_verify_claim(text, api_key):
    """Use Gemini AI to verify the credibility of a claim"""
    if not HAS_GEMINI:
        return None

    try:
        model = get_gemini_client(api_key)
        if not model:
            return None
            
        prompt = f"""You are an expert fact-checker. Analyze this news article/claim carefully.

ARTICLE:
{text[:2000]}

ANALYZE FOR:
1. Factual accuracy - Are the claims verifiable?
2. Source credibility - Are sources properly attributed?
3. Evidence quality - Is there solid evidence or just opinions?
4. Emotional manipulation - Does it use sensational language?
5. Logical fallacies - Any logical errors or false reasoning?
6. Red flags - Missing sources, exaggeration, unverified claims?
7. Conspiracy indicators - Unsubstantiated theories?

PROVIDE YOUR ASSESSMENT AS:
- CREDIBILITY LEVEL: HIGH / MEDIUM / LOW
- KEY FINDINGS: (3-5 bullet points)
- VERDICT: LIKELY_TRUE / MIXED / LIKELY_FALSE / UNVERIFIABLE
- CONFIDENCE: 0-100%"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Gemini API Error: {str(e)}\n\nTip: Make sure your API key is valid and you have internet connection."

def search_news_gnews(query, api_key, max_results=10):
    """Search for related news articles on GNews with quality filtering"""
    try:
        params = {
            "q": query,
            "apikey": api_key,
            "lang": "en",
            "max": max_results,
            "sortby": "relevance"
        }
        resp = requests.get("https://gnews.io/api/v4/search", params=params, timeout=10)

        if resp.status_code != 200:
            return []

        data = resp.json()
        articles = data.get("articles", []) if isinstance(data, dict) else []

        # Filter out low-quality articles
        quality_articles = []
        for article in articles:
            if article.get('title') and article.get('source', {}).get('name') and article.get('url'):
                quality_articles.append(article)

        return quality_articles[:max_results]
    except Exception as e:
        return []

def check_gnews_api(api_key):
    """Return (ok:bool, message:str, details:dict)"""
    if not api_key:
        return False, "No GNEWS_API_KEY set", {}
    try:
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": "test", "apikey": api_key, "max": 1, "lang": "en"},
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("totalArticles", None) or len(data.get("articles", []))
            return True, f"GNews reachable — status 200 — articles found: {total}", {"status_code":200, "total": total}
        elif resp.status_code == 401:
            return False, "GNews returned 401 Unauthorized - API key invalid or expired", {"status_code":401, "text": resp.text}
        else:
            return False, f"GNews returned status {resp.status_code}", {"status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        return False, f"GNews request failed: {str(e)}", {}

def translate_text(text, target_lang='en', api_key=None):
    """Translate text using Gemini API"""
    if not HAS_GEMINI or not api_key:
        return text  # Return original if no API
        
    try:
        model = get_gemini_client(api_key)
        if not model:
            return text
            
        prompt = f"""Translate the following text to {target_lang}. 
        Return ONLY the translated text, no explanations.
        
        Text:
        {text[:1000]}""" # Limit length to avoid quota issues
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return text # Fallback to original
