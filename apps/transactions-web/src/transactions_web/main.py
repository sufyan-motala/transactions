from contextlib import asynccontextmanager
from itertools import groupby
from datetime import datetime
import secrets
import uvicorn
from fastapi import FastAPI, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select
from pathlib import Path

from .db import create_db_and_tables, get_session, User, Connection
from . import auth, service
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, https_only=False, max_age=60*60*24*30)

# Point to local templates directory
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(static_dir / "icons/favicon.png")


@app.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon():
    return FileResponse(static_dir / "icons/apple-touch-icon.png")


@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_icon_precomposed():
    return FileResponse(static_dir / "icons/apple-touch-icon.png")


# --- Custom Filters (Updated for Core Objects) ---
def format_currency(value):
    return f"${float(value):.2f}"


def format_date(value):
    # Core returns datetime objects, not timestamps
    if isinstance(value, datetime):
        return value.strftime("%a, %b %d")
    # Fallback for old timestamps if any
    return datetime.fromtimestamp(value).strftime("%a, %b %d")


def format_month(value):
    if isinstance(value, datetime):
        return value.strftime("%B %Y")
    return datetime.fromtimestamp(value).strftime("%B %Y")


templates.env.filters["currency"] = format_currency
templates.env.filters["date"] = format_date
templates.env.filters["month"] = format_month


# --- Dependencies & Helpers ---
def render(request: Request, name: str, context: dict = {}):
    if not request.session.get("csrf_token"):
        request.session["csrf_token"] = secrets.token_hex(32)
    ctx = {
        "request": request,
        "user": request.session.get("user"),
        "csrf_token": request.session.get("csrf_token", ""),
        "flash_error": request.session.pop("flash_error", None),
        **context,
    }
    return templates.TemplateResponse(name, ctx)


def group_transactions(txns):
    grouped = []
    # Data is already sorted by date desc from service
    for k, g in groupby(txns, key=lambda x: format_month(x.date)):
        grouped.append((k, list(g)))
    return grouped


# --- Routes ---


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render(request, "register.html")


@app.post("/register", dependencies=[Depends(auth.validate_csrf)])
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    if session.exec(select(User).where(User.username == username)).first():
        return render(request, "register.html", {"error": "Username taken"})

    user = User(username=username, hashed_password=auth.get_password_hash(password))
    session.add(user)
    session.commit()

    auth.login_user(request, user.username)
    return RedirectResponse("/", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render(request, "login.html")


@app.post("/login", dependencies=[Depends(auth.validate_csrf)])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not auth.verify_password(password, user.hashed_password):
        return render(request, "login.html", {"error": "Invalid credentials"})

    auth.login_user(request, user.username)
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    auth.logout_user(request)
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    # 1. Check for connections
    connections = session.exec(
        select(Connection).where(Connection.user_id == user.id)
    ).all()
    has_conn = bool(connections)

    # 2. Load CACHED data immediately
    txns, errors = await service.get_dashboard_data(session, user.id)
    grouped = group_transactions(txns)

    # Calculate last sync time for display
    last_synced = "Never"
    if connections:
        # Find the most recent sync time
        times = [c.last_synced_at for c in connections if c.last_synced_at]
        if times:
            last_synced = max(times).strftime("%I:%M %p")

    return render(
        request,
        "dashboard.html",
        {
            "has_connections": has_conn,
            "grouped_transactions": grouped,
            "errors": errors,
            "last_synced": last_synced,
        },
    )


@app.get("/transactions-sync", response_class=HTMLResponse)
async def transactions_sync(
    request: Request,
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    """
    Triggered by HTMX on load.
    1. Fetches fresh data from Bank.
    2. Updates Cache.
    3. Returns rendered rows.
    """
    txns, errors = await service.sync_data(session, user.id)
    grouped = group_transactions(txns)

    return render(
        request,
        "partials/transaction_rows.html",
        {
            "grouped_transactions": grouped,
            "errors": errors,
            "last_synced": datetime.now().strftime("%I:%M %p"),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    connections = session.exec(
        select(Connection).where(Connection.user_id == user.id)
    ).all()

    # FETCH ACCOUNTS IMMEDIATELY (Cache-First)
    accounts_data = await service.get_accounts(session, user.id)

    return render(
        request,
        "settings.html",
        {
            "connections": connections,
            "accounts": accounts_data,  # Pass data directly to template
        },
    )


@app.get("/settings/accounts-partial", response_class=HTMLResponse)
async def accounts_partial(
    request: Request,
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    accounts = await service.get_accounts(session, user.id)
    return render(request, "partials/account_rows.html", {"accounts": accounts})


@app.post("/connect", dependencies=[Depends(auth.validate_csrf)])
async def connect_bank(
    request: Request,
    token: str = Form(...),
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    try:
        await service.add_connection(session, user.id, token)
    except Exception as e:
        request.session["flash_error"] = f"Connection failed: {str(e)}"
    return RedirectResponse("/settings", status_code=303)


@app.post("/disconnect/{conn_id}", dependencies=[Depends(auth.validate_csrf)])
async def disconnect_bank(
    conn_id: int,
    user: User = Depends(auth.require_user),
    session: Session = Depends(get_session),
):
    conn = session.get(Connection, conn_id)
    if conn and conn.user_id == user.id:
        session.delete(conn)
        session.commit()
    return RedirectResponse("/settings", status_code=303)


def start():
    """Entry point for script"""
    uvicorn.run("transactions_web.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
