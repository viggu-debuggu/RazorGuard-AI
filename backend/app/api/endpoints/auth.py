from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, RefreshToken
from app.schemas.auth import UserRegister, Token, UserOut, UserLogin
from app.api.dependencies.auth import (
    get_password_hash,
    verify_password,
    create_access_token
)

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_analyst(payload: UserRegister, db: Session = Depends(get_db)):
    """Registers a new risk analyst account."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyst email already registered."
        )

    # First user is automatically Super Admin, subsequent users are Analysts
    num_users = db.query(User).count()
    role = "Super Admin" if num_users == 0 else "Analyst"

    hashed_pw = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hashed_pw,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login_analyst(payload: UserLogin, db: Session = Depends(get_db)):
    """Analyst login endpoint returning secure JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # Generate token
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(days=7))
    
    # Store refresh token hash in DB
    ref = RefreshToken(user_id=user.id, token_hash=refresh_token, expires_at=datetime.utcnow() + timedelta(days=7))
    db.add(ref)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/oauth2-login", include_in_schema=False)
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow helper for Swagger UI interactive testing."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


