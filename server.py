from fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from typing import List

import oauth_manager
import email_service
import memory
import config_manager

# ---------------------------------------------------
# MCP INIT
# ---------------------------------------------------
mcp = FastMCP("Email Copilot")

# ---------------------------------------------------
# MCP TOOLS (Protected)
# ---------------------------------------------------
@mcp.tool()
def get_auth_status() -> str:
    if oauth_manager.is_authenticated():
        creds = oauth_manager.load_credentials()
        email = (
            creds.id_token.get("email")
            if creds.id_token else "Connected Account"
        )
        return f"Authenticated: {email}"
    return "Not Authenticated"

@mcp.tool()
def get_authorization_url() -> str:
    return oauth_manager.get_authorization_url()

@mcp.tool()
def list_unread_emails() -> List[dict]:
    if not oauth_manager.is_authenticated():
        return [{"error": "Not authenticated"}]
    return [e.model_dump() for e in email_service.get_unread_emails()]

# ---------------------------------------------------
# FASTAPI APP (Public Routes)
# ---------------------------------------------------
app = FastAPI(title="Email Copilot MCP Server")

# ---------------------------------------------------
# OAUTH CALLBACK (PUBLIC)
# ---------------------------------------------------
@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return HTMLResponse("<h3>No authorization code received</h3>")

    try:
        oauth_manager.authorize_with_code(code)
        return HTMLResponse("""
            <h2>✅ Authentication Successful!</h2>
            <p>You can now close this tab and return to MCP Inspector.</p>
        """)
    except Exception as e:
        return HTMLResponse(f"<h3>Auth Failed</h3><p>{str(e)}</p>")

# ---------------------------------------------------
# PRIVACY POLICY (PUBLIC)
# ---------------------------------------------------
@app.get("/privacy")
async def privacy():
    return HTMLResponse("""
    <h1>Email Copilot MCP Privacy Policy</h1>
    <p>This application accesses Gmail data via Google OAuth2.</p>
    <h3>Data Accessed</h3>
    <ul>
        <li>Email subject</li>
        <li>Email sender</li>
        <li>Email body</li>
    </ul>
    <h3>Usage</h3>
    <p>Data is used only to generate AI-powered draft replies.</p>
    <h3>Storage</h3>
    <p>We do not permanently store your email data.</p>
    <h3>Sharing</h3>
    <p>No Google user data is shared with third parties.</p>
    <h3>Security</h3>
    <p>OAuth tokens are securely stored.</p>
    <p>Contact: sachin219566@gmail.com</p>
    """)

# ---------------------------------------------------
# TERMS OF SERVICE (PUBLIC)
# ---------------------------------------------------
@app.get("/terms")
async def terms():
    return HTMLResponse("""
    <h1>Email Copilot MCP Terms of Service</h1>
    <p>By using this application, you allow Gmail access via OAuth.</p>
    <p>Service is provided "as is".</p>
    <p>We are not liable for any damages.</p>
    <p>You may revoke access anytime from your Google Account.</p>
    """)

# ---------------------------------------------------
# MCP HTTP APP (Protected)
# ---------------------------------------------------
mcp_app = mcp.http_app(path="/mcp")

# 🔥 IMPORTANT: Mount MCP ONLY on /mcp
app.mount("/mcp", mcp_app)
