from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, User, Usage, Message
from models import ChatRequest
from middleware.auth import get_current_user
from services.ollama_service import generate_response
from datetime import datetime, date

router = APIRouter()

MODEL_GROUPS = {
    "llama2_7b": "7b",
    "qwen2_7b": "7b",
    "phi": "7b",
    "llama2_14b": "14b",
    "llama2_32b": "32b"
}

LIMITS = {
    "free": {"7b": 100, "14b": 5, "32b": 1},
    "paid": {"7b": float('inf'), "14b": 25, "32b": 10}
}

@router.post("/send")
async def send_message(request: ChatRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if request.model_id not in MODEL_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid model ID")
    
    user_id = current_user["user_id"]
    tier = current_user["tier"]
    group = MODEL_GROUPS[request.model_id]
    
    # Check usage
    usage = db.query(Usage).filter(Usage.user_id == user_id).first()
    if not usage:
        raise HTTPException(status_code=400, detail="Usage record not found")
    
    # Check if reset needed
    if (date.today() - usage.month_start_date).days >= 30:
        usage.month_start_date = date.today()
        usage.model_7b_uses = 0
        usage.model_14b_uses = 0
        usage.model_32b_uses = 0
        db.commit()
    
    current_uses = getattr(usage, f"model_{group}_uses")
    limit = LIMITS[tier][group]
    
    if current_uses >= limit:
        raise HTTPException(status_code=429, detail="Monthly limit reached for this model tier")

    # Calling Ollama
    ollama_res = await generate_response(request.model_id, request.message)
    if "error" in ollama_res:
        if ollama_res["error"] == "timeout":
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif ollama_res["error"] == "unavailable":
            raise HTTPException(status_code=503, detail="Service Unavailable")
        else:
            raise HTTPException(status_code=500, detail="Error communicating with LLM")
            
    ai_text = ollama_res.get("response", "")
    
    # Store message
    msg = Message(
        user_id=user_id,
        model_used=request.model_id,
        user_message=request.message,
        ai_response=ai_text,
        conversation_id=request.conversation_id
    )
    db.add(msg)
    
    # Increment usage
    setattr(usage, f"model_{group}_uses", current_uses + 1)
    db.commit()
    db.refresh(msg)
    
    if not request.conversation_id:
        msg.conversation_id = msg.message_id
        db.commit()
        db.refresh(msg)
    
    return {
        "status": "success",
        "message_id": msg.message_id,
        "ai_response": ai_text,
        "model_used": request.model_id,
        "conversation_id": msg.conversation_id,
        "timestamp": msg.timestamp.isoformat(),
        "uses_remaining": {
            "llama2_7b_qwen2_7b": max(0, LIMITS[tier]["7b"] - usage.model_7b_uses) if tier == "free" else "unlimited",
            "llama2_14b": max(0, LIMITS[tier]["14b"] - usage.model_14b_uses),
            "llama2_32b": max(0, LIMITS[tier]["32b"] - usage.model_32b_uses)
        }
    }

@router.get("/history")
def get_history(conversation_id: int = None, limit: int = 50, offset: int = 0, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    query = db.query(Message).filter(Message.user_id == user_id)
    if conversation_id:
        query = query.filter(Message.conversation_id == conversation_id)
    messages = query.order_by(Message.timestamp.desc()).offset(offset).limit(limit).all()
    count = query.count()
    
    return {
        "messages": [
            {
                "message_id": m.message_id,
                "model_used": m.model_used,
                "user_message": m.user_message,
                "ai_response": m.ai_response,
                "timestamp": m.timestamp.isoformat()
            } for m in messages
        ],
        "total_count": count
    }

@router.get("/conversations")
def get_conversations(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    
    # Identify unique conversations for the user
    subquery = db.query(
        Message.conversation_id,
        func.min(Message.timestamp).label("start_time")
    ).filter(Message.user_id == user_id).group_by(Message.conversation_id).subquery()
    
    # Join back to get the message that started the conversation (for a title)
    conversations = db.query(Message).join(
        subquery,
        (Message.conversation_id == subquery.c.conversation_id) & 
        (Message.timestamp == subquery.c.start_time)
    ).order_by(Message.timestamp.desc()).all()

    return {
        "conversations": [
            {
                "conversation_id": c.conversation_id,
                "title": c.user_message[:30] + ("..." if len(c.user_message) > 30 else ""),
                "timestamp": c.timestamp.isoformat()
            } for c in conversations if c.conversation_id is not None
        ]
    }
