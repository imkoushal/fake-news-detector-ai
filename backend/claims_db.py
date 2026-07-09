import json
import logging
from backend.db import get_db, execute_db, USE_POSTGRES

logger = logging.getLogger("fake_news_api")

def init_seo_claims_db():
    try:
        conn = get_db()
        c = conn.cursor()
        
        timestamp_type = "TIMESTAMP" if USE_POSTGRES else "DATETIME"
        
        c.execute(f'''CREATE TABLE IF NOT EXISTS seo_claims (
            claim_hash TEXT PRIMARY KEY,
            claim_text TEXT NOT NULL,
            verdict TEXT NOT NULL,
            confidence REAL NOT NULL,
            response_json TEXT NOT NULL,
            created_at {timestamp_type} DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
        logger.info("seo_claims table initialized")
    except Exception as e:
        logger.error(f"Failed to init seo_claims db: {e}")

def save_seo_claim(claim_hash: str, text: str, response: dict):
    try:
        verdict = response.get("verdict", "UNVERIFIABLE")
        confidence = response.get("confidence", 0.0)
        
        query = """
            INSERT INTO seo_claims (claim_hash, claim_text, verdict, confidence, response_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(claim_hash) DO NOTHING
        """ if not USE_POSTGRES else """
            INSERT INTO seo_claims (claim_hash, claim_text, verdict, confidence, response_json)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(claim_hash) DO NOTHING
        """
        execute_db(query, (claim_hash, text, verdict, confidence, json.dumps(response)), commit=True)
    except Exception as e:
        logger.error(f"Failed to save seo claim: {e}")

def get_seo_claim(claim_hash: str) -> dict | None:
    try:
        query = "SELECT claim_text, response_json FROM seo_claims WHERE claim_hash = ?" if not USE_POSTGRES else "SELECT claim_text, response_json FROM seo_claims WHERE claim_hash = %s"
        row = execute_db(query, (claim_hash,), fetch="one")
        if row:
            data = json.loads(row[1])
            data["claim_text"] = row[0]  # Always include original claim text
            return data
    except Exception as e:
        logger.error(f"Failed to get seo claim: {e}")
    return None
