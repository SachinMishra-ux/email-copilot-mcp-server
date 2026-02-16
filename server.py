from fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import oauth_manager
import email_service
import memory
import config_manager
from typing import List

# MCP INIT
mcp = FastMCP("Email Copilot")

# ---------------- MCP TOOLS ----------------
@mcp.tool()
def get_auth_status() -> str:
    if oauth_manager.is_authenticated():
        creds = oauth_manager.load_credentials()
        email = (
            creds.id_token.get('email')
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

# ---------------- FASTAPI WRAPPER ----------------
mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(
    title="Email Copilot MCP Server",
    lifespan=mcp_app.router.lifespan_context,
)

app.mount("/", mcp_app)

# ---------------- OAUTH CALLBACK ----------------
@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return HTMLResponse("<h3>No authorization code</h3>")

    try:
        oauth_manager.authorize_with_code(code)
        return HTMLResponse("""
            <h2>✅ Authentication Successful</h2>
            <p>Return to MCP Inspector</p>
        """)
    except Exception as e:
        return HTMLResponse(f"<h3>Auth Failed</h3><p>{str(e)}</p>")
