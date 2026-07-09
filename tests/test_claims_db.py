import pytest
import os
from backend.claims_db import init_seo_claims_db, save_seo_claim, get_seo_claim
from backend.db import get_db

def test_seo_claims_lifecycle():
    # Use SQLite for tests implicitly
    init_seo_claims_db()
    
    hash_key = "test_hash_123"
    text = "This is a test claim"
    response = {"verdict": "LIKELY_TRUE", "confidence": 95.0, "mode": "rag"}
    
    save_seo_claim(hash_key, text, response)
    
    claim = get_seo_claim(hash_key)
    assert claim is not None
    assert claim["verdict"] == "LIKELY_TRUE"
    assert claim["confidence"] == 95.0
    
    # Missing claim
    missing = get_seo_claim("does_not_exist")
    assert missing is None
