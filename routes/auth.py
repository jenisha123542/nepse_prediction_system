from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from utils.security import hash_password, verify_password, create_access_token, get_current_user
from typing import List, Optional
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class AdminCreateUser(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "user"

class AdminUpdateUser(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None   # if provided, will be re-hashed
    role: Optional[str] = None


# ── EXISTING AUTH ROUTES ───────────────────────────────────────────────────────

@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ── ADMIN USER MANAGEMENT ──────────────────────────────────────────────────────

def require_admin(current_user: models.User = Depends(get_current_user)):
    """Dependency: raises 403 if caller is not admin."""
    if current_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user


@router.get("/users", response_model=List[schemas.UserOut])
def get_all_users(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUser,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin creates a new user directly — no email verification flow."""
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    role = payload.role if payload.role in ("user", "admin") else "user"
    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=models.RoleEnum(role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=schemas.UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUpdateUser,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin updates name, email, role, or password of any user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from demoting themselves
    if user.id == current_user.id and payload.role and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    if payload.name  is not None: user.name  = payload.name
    if payload.email is not None:
        clash = db.query(models.User).filter(
            models.User.email == payload.email,
            models.User.id    != user_id
        ).first()
        if clash:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = payload.email
    if payload.role is not None and payload.role in ("user", "admin"):
        user.role = models.RoleEnum(payload.role)
    if payload.password is not None and payload.password.strip():
        user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/suspend", response_model=schemas.UserOut)
def admin_suspend_user(
    user_id: int,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle is_active on a user. Suspended users cannot log in."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")

    user.is_active = not user.is_active   # toggle
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a user. Admin cannot delete themselves."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    db.delete(user)
    db.commit()