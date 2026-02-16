import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from typing import Optional

import config_manager

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
CONFIG_DIR = Path.home() / ".email-copilot"
TOKEN_FILE = CONFIG_DIR / "token.json"

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

# 🔥 MUST MATCH GCP CONSOLE
APP_BASE_URL = "https://horizon.prefect.io"
REDIRECT_URI = f"{APP_BASE_URL}/oauth/callback"


# -------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------
def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _build_flow() -> Flow:
    """Builds OAuth Flow object for cloud deployment."""
    sys_config = config_manager.load_system_config()
    if not sys_config:
        raise ValueError(
            "Application not configured. Run 'configure_mcp_app' first."
        )

    client_config = {
        "web": {
            "client_id": sys_config["client_id"],
            "client_secret": sys_config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


# -------------------------------------------------------
# STEP 1 → LOGIN URL
# -------------------------------------------------------
def get_authorization_url() -> str:
    """Generate Google OAuth login URL."""
    flow = _build_flow()

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    return auth_url


# -------------------------------------------------------
# STEP 2 → GOOGLE CALLBACK HITS MCP SERVER
# -------------------------------------------------------
def authorize_with_code(code: str) -> None:
    """Exchange auth code for access + refresh tokens."""
    flow = _build_flow()

    flow.fetch_token(code=code)

    credentials = flow.credentials

    save_credentials(credentials)

    # Persist logged-in email
    if credentials.id_token and "email" in credentials.id_token:
        config_manager.update_config_field(
            "EMAIL_USER",
            credentials.id_token["email"],
        )


# -------------------------------------------------------
# TOKEN STORAGE
# -------------------------------------------------------
def save_credentials(credentials: Credentials):
    ensure_config_dir()

    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())


def load_credentials() -> Optional[Credentials]:
    if not TOKEN_FILE.exists():
        return None

    creds = Credentials.from_authorized_user_file(
        TOKEN_FILE, SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(creds)

    return creds


# -------------------------------------------------------
# AUTH CHECK
# -------------------------------------------------------
def is_authenticated() -> bool:
    creds = load_credentials()
    return creds is not None and creds.valid


# -------------------------------------------------------
# GMAIL XOAUTH2 STRING
# -------------------------------------------------------
def get_auth_string(user: str, token: str) -> str:
    return f"user={user}\1auth=Bearer {token}\1\1"
