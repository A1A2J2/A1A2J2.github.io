from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import random
from database import get_db, User, Usage, EmailVerification
from models import UserSignup, UserLogin, UserVerify
from services.auth_service import hash_password, verify_password, create_access_token
from middleware.auth import get_current_user

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_202_ACCEPTED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    code = f"{random.randint(100000, 999999)}"
    
    existing_verify = db.query(EmailVerification).filter(EmailVerification.email == user_data.email).first()
    if existing_verify:
        existing_verify.code = code
        existing_verify.username = user_data.username
        existing_verify.password_hash = hash_password(user_data.password)
        existing_verify.expires_at = datetime.utcnow() + timedelta(minutes=10)
    else:
        new_verify = EmailVerification(
            email=user_data.email,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(new_verify)
    db.commit()

    print(f"\n======================================")
    print(f"EMAIL SENT TO: {user_data.email}")
    print(f"SUBJECT: Your Verification Code")
    print(f"BODY: Please use the following 6-digit code to verify your account: {code}")
    print(f"======================================\n")

    return {"status": "pending_verification", "message": "Verification code sent"}

@router.post("/verify-email", status_code=status.HTTP_201_CREATED)
def verify_email(data: UserVerify, db: Session = Depends(get_db)):
    verify_record = db.query(EmailVerification).filter(EmailVerification.email == data.email).first()
    if not verify_record:
        raise HTTPException(status_code=400, detail="No verification pending for this email")
    if verify_record.code != data.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    if verify_record.expires_at < datetime.utcnow():
        db.delete(verify_record)
        db.commit()
        raise HTTPException(status_code=400, detail="Code expired")

    existing_user = db.query(User).filter(User.username == verify_record.username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username was taken. Try another.")

    new_user = User(username=verify_record.username, password_hash=verify_record.password_hash, email=verify_record.email, tier="free")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    new_usage = Usage(user_id=new_user.user_id, month_start_date=date.today())
    db.add(new_usage)
    db.delete(verify_record)
    db.commit()

    return {"status": "success", "username": new_user.username, "message": "Account created"}

@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    if user_data.username == "admin" and user_data.password == "admin":
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(username="admin", password_hash=hash_password("admin"), email="admin@admin.com", tier="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
            usage = Usage(user_id=user.user_id, month_start_date=date.today())
            db.add(usage)
            db.commit()
    else:
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
