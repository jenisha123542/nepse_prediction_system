from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.security import get_current_user, require_admin
import models

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# --- User Dashboard ---
@router.get("/summary")
def user_summary(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns summary data for the logged-in user."""
    return {
        "user": current_user.name,
        "role": current_user.role,
        "message": "Welcome to your dashboard!",
        # Add your real analytics queries here
        "stats": {
            "total_reports": 0,
            "active_sessions": 1,
        }
    }

# --- Admin Dashboard ---
@router.get("/admin/stats")
def admin_stats(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: returns platform-wide statistics."""
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    admin_count = db.query(models.User).filter(models.User.role == "admin").count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_count": admin_count,
    }

@router.get("/admin/users")
def list_users(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: returns all users."""
    users = db.query(models.User).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active}
        for u in users
    ]