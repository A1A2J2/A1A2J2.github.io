from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Usage
from middleware.auth import get_current_user
from datetime import date, timedelta

router = APIRouter()

LIMITS = {
    "free": {"7b": 100, "8b": 100, "13b": 5},
    "paid": {"7b": "unlimited", "8b": "unlimited", "13b": 25},
    "admin": {"7b": "unlimited", "8b": "unlimited", "13b": "unlimited"}
}

@router.get("/remaining")
def get_remaining_uses(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    tier = current_user["tier"]
    
    usage = db.query(Usage).filter(Usage.user_id == user_id).first()
    if not usage:
        raise HTTPException(status_code=404, detail="Usage record not found")
        
    if (date.today() - usage.month_start_date).days >= 30:
        usage.month_start_date = date.today()
        usage.model_7b_uses = 0
        usage.model_8b_uses = 0
        usage.model_13b_uses = 0
        db.commit()

    return {
        "tier": tier,
        "usage": {
            "llama2_7b_qwen2_7b": {
                "used": usage.model_7b_uses,
                "limit": LIMITS[tier]["7b"],
                "remaining": LIMITS[tier]["7b"] - usage.model_7b_uses if LIMITS[tier]["7b"] != "unlimited" else None
            },
            "llama3_8b": {
                "used": usage.model_8b_uses,
                "limit": LIMITS[tier]["8b"],
                "remaining": LIMITS[tier]["8b"] - usage.model_8b_uses if LIMITS[tier]["8b"] != "unlimited" else None
            },
            "llama2_13b": {
                "used": usage.model_13b_uses,
                "limit": LIMITS[tier]["13b"],
                "remaining": LIMITS[tier]["13b"] - usage.model_13b_uses if LIMITS[tier]["13b"] != "unlimited" else None
            }
        },
        "month_resets_on": (usage.month_start_date + timedelta(days=30)).isoformat()
    }
