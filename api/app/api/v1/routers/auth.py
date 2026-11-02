"""Auth router: login and current user."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidCredentials
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    get_current_user,
    verify_password,
)
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    email = body.email.lower()
    user = db.scalar(select(StaffUser).where(StaffUser.email == email))
    # Always run one bcrypt check so an unknown email takes as long as a wrong password.
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        write_audit(
            db,
            actor_id=None,
            action="login.failure",
            target_type="staff_user",
            target_id=None,
            details={"email": email},
        )
        db.commit()
        raise InvalidCredentials()
    token, expires_at = create_access_token(user)
    write_audit(
        db,
        actor_id=user.id,
        action="login.success",
        target_type="staff_user",
        target_id=str(user.id),
        details={},
    )
    db.commit()
    return LoginResponse(
        access_token=token, expires_at=expires_at, user=UserOut.model_validate(user)
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[StaffUser, Depends(get_current_user)]) -> StaffUser:
    return user
