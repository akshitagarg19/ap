from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import httpx, os
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="u3hw8vhs83hfs8fhwfjkwhfj34hflj93")

# Load values from .env
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get Google's OAuth 2.0 endpoints
async def get_google_provider_cfg():
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_DISCOVERY_URL)
        return resp.json()

@app.get("/")
async def login():
    cfg = await get_google_provider_cfg()
    auth_endpoint = cfg["authorization_endpoint"]
    request_uri = auth_endpoint + "?" + urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "prompt": "consent",
        "access_type": "offline"
    })
    return RedirectResponse(request_uri)

@app.get("/auth")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(content={"error": "Missing code in callback"}, status_code=400)

    cfg = await get_google_provider_cfg()
    token_endpoint = cfg["token_endpoint"]

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_endpoint,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if token_response.status_code != 200:
            return JSONResponse(content={"error": "Token exchange failed"}, status_code=400)

        token_json = token_response.json()
        request.session["id_token"] = token_json["id_token"]
        return RedirectResponse("/id_token")

@app.get("/id_token")
def get_id_token(request: Request):
    id_token = request.session.get("id_token")
    if not id_token:
        return JSONResponse(content={"error": "Not logged in"}, status_code=401)
    return JSONResponse(content={"id_token": id_token})
print("Google Client ID:", GOOGLE_CLIENT_ID)
