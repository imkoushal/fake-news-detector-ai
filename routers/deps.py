"""
Shared dependencies for all routers.
Exposes globals, helpers, and imports that multiple route modules need.
"""
from __future__ import annotations

import os
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict

from backend.db import get_db, ph, execute_db, USE_POSTGRES, BASE_DIR
from backend.auth import (
    hash_password, verify_password, sanitize_preview,
    get_user_from_token, create_session, new_session_token,
    hash_session_token, SESSION_TTL_DAYS,
)
from backend.cache import ClaimCache

from utils import clean_text
from meta_features import extract_single as compute_meta_features
from enhanced_features import detect_fake_news_red_flags

logger = logging.getLogger("fake_news_api")
