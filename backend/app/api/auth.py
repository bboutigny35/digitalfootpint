from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_session,
    get_current_user,
    require_admin,
    require_csrf,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import AuditEvent, AuthSession, User
from app.schemas.auth import Credentials, CsrfRead, SessionRead, UserCreate, UserRead
from app.security.passwords import hash_password, hasher, verify_password
from app.security.sessions import new_token, token_digest

router = APIRouter(prefix="/auth", tags=["authentification"])
_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_attempt_lock = Lock()


def _client_key(request: Request, email: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{email.lower()}"


def _rate_limit(key: str) -> None:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.login_window_seconds)
    with _attempt_lock:
        attempts = _attempts[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= settings.login_max_attempts:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Trop de tentatives")
        attempts.append(datetime.now(UTC))


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "df_session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/bootstrap", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def bootstrap(
    payload: Credentials, response: Response, db: Session = Depends(get_db)
) -> SessionRead:
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(status.HTTP_409_CONFLICT, "L'initialisation a déjà été effectuée")
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        is_admin=True,
    )
    db.add(user)
    db.flush()
    token, csrf = new_token(), new_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=token_digest(token),
        csrf_hash=token_digest(csrf),
        expires_at=datetime.now(UTC) + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add_all(
        [
            auth_session,
            AuditEvent(
                actor_id=user.id, action="auth.bootstrap", resource_type="user", resource_id=user.id
            ),
        ]
    )
    db.commit()
    _set_cookie(response, token)
    return SessionRead(user=UserRead.model_validate(user), csrf_token=csrf)


@router.post("/login", response_model=SessionRead)
def login(
    payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)
) -> SessionRead:
    key = _client_key(request, str(payload.email))
    _rate_limit(key)
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    db.query(AuthSession).filter(AuthSession.expires_at <= datetime.now(UTC)).delete()
    with _attempt_lock:
        _attempts.pop(key, None)
    token, csrf = new_token(), new_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=token_digest(token),
        csrf_hash=token_digest(csrf),
        expires_at=datetime.now(UTC) + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add_all(
        [
            auth_session,
            AuditEvent(
                actor_id=user.id,
                action="auth.login",
                resource_type="session",
                resource_id=auth_session.id,
            ),
        ]
    )
    db.commit()
    _set_cookie(response, token)
    return SessionRead(user=UserRead.model_validate(user), csrf_token=csrf)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/csrf", response_model=CsrfRead)
def csrf_token(
    response: Response,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> CsrfRead:
    """Rotate and return a CSRF token for an existing cookie session."""
    csrf = new_token()
    auth_session.csrf_hash = token_digest(csrf)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return CsrfRead(csrf_token=csrf)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
def logout(
    response: Response,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    db.delete(auth_session)
    db.commit()
    response.delete_cookie("df_session", path="/")


@router.post("/refresh", response_model=SessionRead, dependencies=[Depends(require_csrf)])
def refresh_session(
    response: Response,
    auth_session: AuthSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> SessionRead:
    user = auth_session.user
    db.delete(auth_session)
    token, csrf = new_token(), new_token()
    replacement = AuthSession(
        user_id=user.id,
        token_hash=token_digest(token),
        csrf_hash=token_digest(csrf),
        expires_at=datetime.now(UTC) + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add_all(
        [
            replacement,
            AuditEvent(
                actor_id=user.id,
                action="auth.refresh",
                resource_type="session",
                resource_id=replacement.id,
            ),
        ]
    )
    db.commit()
    _set_cookie(response, token)
    return SessionRead(user=UserRead.model_validate(user), csrf_token=csrf)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_user(
    payload: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce compte existe déjà")
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="user.create",
            resource_type="user",
            resource_id=user.id,
            details={"is_admin": user.is_admin},
        )
    )
    db.commit()
    db.refresh(user)
    return user
