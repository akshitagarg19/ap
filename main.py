import os
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import httpx
from urllib.parse import urlencode

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/auth/callback"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

@app.get("/")
async def root(request: Request):
    if "id_token" not in request.session:
        return RedirectResponse("/login")
    return {"message": "Welcome! You are logged in."}

@app.get("/login")
async def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": REDIRECT_URI,
        "prompt": "consent"
    }
    url = f"{GOOGLE_AUTH_URI}?{urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URI, data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    token_data = resp.json()
    request.session["id_token"] = token_data.get("id_token")

    return RedirectResponse("/id_token")

@app.get("/id_token")
async def get_id_token(request: Request):
    id_token = request.session.get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse(content={"id_token": id_token})
