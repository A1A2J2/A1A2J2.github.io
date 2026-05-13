from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from database import get_db, User, Usage
from models import UserSignup, UserLogin
from services.auth_service import hash_password, verify_password, create_access_token
from middleware.auth import get_current_user

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # Check if username or email exists
    existing_user = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    # Create new user
    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        tier="free"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initialize usage
    new_usage = Usage(
        user_id=new_user.user_id,
        month_start_date=date.today()
    )
    db.add(new_usage)
    db.commit()

    return {
        "status": "success",
        "user_id": new_user.user_id,
        "username": new_user.username,
        "tier": new_user.tier,
        "message": "Account created successfully"
    }

@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Generate token
    token = create_access_token({
        "user_id": user.user_id,
        "username": user.username,
        "tier": user.tier
    })

    return {
        "token": token,
        "username": user.username,
        "tier": user.tier
    }

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "tier": user.tier,
        "joined_date": user.created_at.isoformat()
    }
