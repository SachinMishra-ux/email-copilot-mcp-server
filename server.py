import os
import sys
from fastmcp import FastMCP
from fastapi import Request
from fastapi.responses import HTMLResponse
from models import EmailMetadata, DraftReply
import email_service
import memory
import config_manager
import oauth_manager
from typing import List

# ----------------------------------------------------
# 🔥 IMPORTANT: PUBLIC DOMAIN REDIRECT URI
# ----------------------------------------------------
REDIRECT_URI = "https://horizon.prefect.io/oauth/callback"

# ----------------------------------------------------
# MCP INIT
# ----------------------------------------------------
mcp = FastMCP("Email Copilot")

# ----------------------------------------------------
# OAUTH CALLBACK ENDPOINT (THIS WAS MISSING ❌)
# ----------------------------------------------------
@mcp.app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return HTMLResponse("<h3>Authorization Failed ❌</h3><p>No code received</p>")

    try:
        oauth_manager.authorize_with_code(code)
        return HTMLResponse("""
            <h2>✅ Google Authentication Successful!</h2>
            <p>You may now close this tab and return to MCP Inspector.</p>
        """)
    except Exception as e:
        return HTMLResponse(f"<h3>Auth Failed ❌</h3><p>{str(e)}</p>")

# ----------------------------------------------------
# AUTH STATUS
# ----------------------------------------------------
@mcp.tool()
def get_auth_status() -> str:
    if oauth_manager.is_authenticated():
        creds = oauth_manager.load_credentials()
        email = (creds.id_token.get('email') if creds.id_token else None) or 'Connected Account'
        return f"Authenticated: Using Google OAuth2 for {email}."

    return "Not Authenticated. Please use 'get_authorization_url' to login."

# ----------------------------------------------------
# AUTH URL GENERATOR (UPDATED)
# ----------------------------------------------------
@mcp.tool()
def get_authorization_url() -> str:
    if not config_manager.is_app_configured():
        return (
            "Error: Application not configured.\n\n"
            "Run 'configure_mcp_app' with Client ID and Secret."
        )
    try:
        url = oauth_manager.get_authorization_url()
        return f"Login using this URL:\n{url}"
    except Exception as e:
        return f"Error generating auth URL: {str(e)}"

# ----------------------------------------------------
# EMAIL TOOLS
# ----------------------------------------------------
@mcp.tool()
def list_unread_emails() -> List[dict]:
    if not oauth_manager.is_authenticated():
        return [{"error": "Not authenticated"}]

    emails = email_service.get_unread_emails()
    if not emails:
        return [{"message": "No unread emails"}]
    return [e.model_dump() for e in emails]

@mcp.tool()
def search_emails(query: str) -> List[dict]:
    if not oauth_manager.is_authenticated():
        return [{"error": "Not authenticated"}]

    emails = email_service.search_emails(query)
    if not emails:
        return [{"message": f"No emails matching '{query}'"}]
    return [e.model_dump() for e in emails]

@mcp.tool()
def draft_reply(email_id: str) -> str:
    if not oauth_manager.is_authenticated():
        return "Error: Not authenticated."

    email = email_service.get_email_by_id(email_id)
    if not email:
        return f"Error: Email {email_id} not found."

    style = memory.load_style()
    greeting = style.preferred_greetings[0] if style.preferred_greetings else "Hi"
    closing = style.preferred_closings[0] if style.preferred_closings else "Best,"

    draft = f"{greeting} {email.sender.split('<')[0].strip() if '<' in email.sender else email.sender.split('@')[0]},\n\n"
    draft += f"Thank you for your email regarding '{email.subject}'.\n\n"
    draft += "I'm reviewing your request and will update you shortly.\n\n"
    draft += f"{closing}\n"

    return draft

@mcp.tool()
def save_draft(to_email: str, subject: str, body: str) -> str:
    if not oauth_manager.is_authenticated():
        return "Error: Not authenticated."

    success = email_service.save_draft_message(to_email, subject, body)
    return "Draft saved." if success else "Failed to save draft."

@mcp.tool()
def send_email(to_email: str, subject: str, body: str) -> str:
    if not oauth_manager.is_authenticated():
        return "Error: Not authenticated."

    success = email_service.send_email_message(to_email, subject, body)
    return f"Email sent to {to_email}" if success else "Send failed"

# ----------------------------------------------------
# SERVER START
# ----------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)

