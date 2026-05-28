from fastapi import APIRouter, Depends, HTTPException, Response, status, Cookie
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    TenantCreate,
)
from app.api.v1.deps import get_current_user
from jose import JWTError

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    tenant_data: TenantCreate,
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    existing_tenant = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Slug já está em uso",
        )

    tenant = Tenant(name=tenant_data.name, slug=tenant_data.slug)
    db.add(tenant)
    db.flush()

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email == user_data.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email já cadastrado neste tenant",
        )

    user = User(
        tenant_id=tenant.id,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=UserRole.OWNER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    # Resolve tenant pelo slug primeiro — 401 genérico para não vazar existência
    tenant = db.query(Tenant).filter(Tenant.slug == body.slug).first()

    user = (
        db.query(User)
        .filter(
            User.tenant_id == tenant.id if tenant else None,
            User.email == body.email,
        )
        .first()
        if tenant
        else None
    )

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta desativada",
        )

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id)
    refresh_token = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado",
    )

    if refresh_token is None:
        raise credentials_exception

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "refresh":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    tenant_id: str | None = payload.get("tenant_id")

    if user_id is None or tenant_id is None:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
    )

    if user is None or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id)
    new_refresh_token = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("refresh_token")
    return {"detail": "Logout realizado com sucesso"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Retorna os dados do usuário autenticado."""
    return current_user
