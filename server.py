from fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from typing import List

import oauth_manager
import email_service

# MCP INIT
mcp = FastMCP("Email Copilot")

# MCP TOOLS
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

# PUBLIC FASTAPI APP
app = FastAPI()

# OAUTH CALLBACK
@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return HTMLResponse("<h3>No authorization code</h3>")

    try:
        oauth_manager.authorize_with_code(code)
        return HTMLResponse("""
            <h2>✅ Authentication Successful</h2>
            <p>You can close this tab.</p>
        """)
    except Exception as e:
        return HTMLResponse(f"<h3>Auth Failed</h3><p>{str(e)}</p>")

# PRIVACY POLICY
@app.get("/privacy")
async def privacy():
    return HTMLResponse("<h2>Email Copilot MCP Privacy Policy</h2>")

# TERMS
@app.get("/terms")
async def terms():
    return HTMLResponse("<h2>Email Copilot MCP Terms</h2>")

# MCP PROTECTED ROUTES
mcp_app = mcp.http_app(path="/mcp")
app.mount("/mcp", mcp_app)
