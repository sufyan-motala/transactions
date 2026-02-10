import secrets
from fastapi import Request, Depends, HTTPException, status, Form
from sqlmodel import Session, select
from passlib.context import CryptContext
from .db import get_session, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    username = request.session.get("user")
    if not username:
        return None
    return session.exec(select(User).where(User.username == username)).first()


async def require_user(
    request: Request, user: User = Depends(get_current_user)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return user


async def validate_csrf(request: Request, csrf_token: str = Form(...)):
    session_token = request.session.get("csrf_token")
    if not session_token or not secrets.compare_digest(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF Token")


def login_user(request: Request, username: str):
    request.session["user"] = username
    request.session["csrf_token"] = secrets.token_hex(32)


def logout_user(request: Request):
    request.session.clear()
