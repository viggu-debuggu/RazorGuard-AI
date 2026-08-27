import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, RefreshToken
from app.schemas.auth import UserRegister, Token, UserOut, UserLogin, TokenRefreshRequest
from app.api.dependencies.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.core.limiter import limiter

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")  # Set to 20/minute for demo rehearsal; production value should be lower (e.g. 5/minute)
def register_analyst(payload: UserRegister, request: Request, db: Session = Depends(get_db)):
    """Registers a new risk analyst account."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyst email already registered."
        )

    # First user is automatically Super Admin only if ALLOW_FIRST_USER_ADMIN is set to True
    from app.core.config import settings
    if settings.ALLOW_FIRST_USER_ADMIN:
        num_users = db.query(User).count()
        role = "Super Admin" if num_users == 0 else "Analyst"
    else:
        role = "Analyst"

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
@limiter.limit("20/minute")  # Set to 20/minute for demo rehearsal; production value should be lower (e.g. 5/minute)
def login_analyst(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Analyst login endpoint returning secure JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # Generate token
    import uuid
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(
        data={"sub": user.email, "jti": str(uuid.uuid4())}, 
        expires_delta=timedelta(days=7)
    )
    
    # Store refresh token hash in DB
    hashed_refresh = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    ref = RefreshToken(user_id=user.id, token_hash=hashed_refresh, expires_at=datetime.utcnow() + timedelta(days=7))
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


@router.post("/refresh")
def refresh_token(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Redeems a refresh token to generate a new access token and rotate the refresh token."""
    # Decode the refresh token to check the type claim
    from jose import JWTError, jwt
    from app.core.config import settings
    try:
        decoded_payload = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if decoded_payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type."
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )

    hashed_refresh = hashlib.sha256(payload.refresh_token.encode("utf-8")).hexdigest()
    
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == hashed_refresh).first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )
        
    if db_token.expires_at < datetime.utcnow():
        db.delete(db_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired refresh token."
        )
        
    user = db_token.user
    access_token = create_access_token(data={"sub": user.email})
    
    # Rotate the refresh token
    import uuid
    new_refresh_token = create_refresh_token(
        data={"sub": user.email, "jti": str(uuid.uuid4())}, 
        expires_delta=timedelta(days=7)
    )
    new_hashed_refresh = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()
    
    db_token.token_hash = new_hashed_refresh
    db_token.expires_at = datetime.utcnow() + timedelta(days=7)
    db.add(db_token)
    db.commit()
    
    # Construct UserOut representation manually to return it
    user_out = {
        "id": user.id,
        "uuid": user.uuid,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": user_out
    }


