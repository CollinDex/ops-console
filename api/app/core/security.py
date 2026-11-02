"""Password hashing, JWT creation/validation and role checks."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Forbidden, NotAuthenticated, TokenExpired
from app.db.session import get_db
from app.models.enums import Role
from app.models.staff_user import StaffUser

JWT_ALGORITHM = "HS256"

# auto_error=False: FastAPI would answer 403 for a missing header, and we want 401.
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # e.g. a password over bcrypt's 72-byte limit can never match
        return False


# Verified against when the email is unknown, so both login paths cost one bcrypt check.
DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_access_token(user: StaffUser, *, ttl_minutes: int | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = settings.jwt_ttl_minutes if ttl_minutes is None else ttl_minutes
    expires_at = now + timedelta(minutes=ttl)
    claims = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM), expires_at


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> StaffUser:
    if credentials is None:
        raise NotAuthenticated()
    try:
        claims = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired() from exc
    except jwt.PyJWTError as exc:
        raise NotAuthenticated() from exc
    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise NotAuthenticated() from exc
    # The role is read from the DB, never trusted from the token claim.
    user = db.get(StaffUser, user_id)
    if user is None:
        raise NotAuthenticated()
    request.state.actor_id = str(user.id)
    return user


def require_roles(
    *roles: Role, action: str = "access this resource"
) -> Callable[[StaffUser], StaffUser]:
    def dependency(user: Annotated[StaffUser, Depends(get_current_user)]) -> StaffUser:
        if user.role not in roles:
            raise Forbidden(f"Your role ({user.role.value.replace('_', ' ')}) cannot {action}.")
        return user

    return dependency
