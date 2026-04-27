"""
Простая аутентификация для AdminPanel через сессионный cookie.
Один пользователь — логин/пароль из .env
"""
from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import hashlib
import hmac
from app.config import settings


def _make_token(login: str) -> str:
    """Простой HMAC токен"""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        login.encode(),
        hashlib.sha256
    ).hexdigest()


def check_admin(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    if not token:
        return False
    expected = _make_token(settings.ADMIN_LOGIN)
    return hmac.compare_digest(token, expected)


def require_admin(request: Request):
    if not check_admin(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def admin_login_response(response: Response, login: str, password: str) -> bool:
    if login == settings.ADMIN_LOGIN and password == settings.ADMIN_PASSWORD:
        token = _make_token(login)
        response.set_cookie(
            "admin_token", token,
            httponly=True, samesite="lax",
            max_age=86400 * 7  # 7 дней
        )
        return True
    return False
