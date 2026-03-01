# src/data/kite_client.py

import os
import json
import logging
from typing import Tuple, Optional
from kiteconnect import KiteConnect


SESSION_FILE = ".kite_session.json"


def load_session_or_env() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load API credentials from environment variables or persisted session file.
    """
    api_key = os.getenv("ZERODHA_API_KEY")
    api_secret = os.getenv("ZERODHA_API_SECRET")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")

    # Try persisted session file
    if not access_token and os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                sess = json.load(f)
                access_token = sess.get("access_token")
                if not api_key:
                    api_key = sess.get("api_key")
        except Exception:
            logging.exception("Failed reading .kite_session.json")

    return api_key, api_secret, access_token


def persist_session(api_key: str, access_token: str):
    """
    Save session token for reuse.
    """
    with open(SESSION_FILE, "w") as f:
        json.dump({"api_key": api_key, "access_token": access_token}, f)


def get_kite(api_key: str, access_token: Optional[str] = None) -> KiteConnect:
    """
    Create KiteConnect instance.
    """
    kite = KiteConnect(api_key=api_key)
    if access_token:
        kite.set_access_token(access_token)
    return kite