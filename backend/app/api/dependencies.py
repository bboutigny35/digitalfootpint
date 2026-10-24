from datetime import UTC, datetime

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import AuthSession, User
from app.security.sessions import token_digest, tokens_match


def get_current_session(
    request: Request,
    session_token: str | None = Cookie(default=None, alias="df_session"),
    db: Session = Depends(get_db),
) -> AuthSession:
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")
    auth_session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_digest(session_token))
    )
    if auth_session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée")
    if auth_session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        db.delete(auth_session)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée")
    request.state.auth_session = auth_session
    return auth_session


def get_current_user(auth_session: AuthSession = Depends(get_current_session)) -> User:
    return auth_session.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
    return user


def require_csrf(
    auth_session: AuthSession = Depends(get_current_session),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_token or not tokens_match(csrf_token, auth_session.csrf_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Jeton CSRF invalide")
