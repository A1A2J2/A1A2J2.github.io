from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, User, Usage, Message
from models import ChatRequest
from middleware.auth import get_current_user
from services.ollama_service import generate_response
from datetime import datetime, date, timedelta

router = APIRouter()

MODEL_GROUPS = {
    "llama2_7b": "7b",
    "qwen2_7b": "7b",
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
    ollama_model = request.model_id.replace("_", ":")
    
    # Enhance message with internet context if needed
    enhanced_msg = await enhance_with_internet(request.message)
    messages_payload = [{"role": "user", "content": enhanced_msg}]
    
    ollama_res = await generate_response(ollama_model, messages_payload)
    if "error" in ollama_res:
        if ollama_res["error"] == "timeout":
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif ollama_res["error"] == "unavailable":
            raise HTTPException(status_code=503, detail="Service Unavailable")
        elif ollama_res["error"] == "not_found":
            raise HTTPException(status_code=404, detail=f"Model '{ollama_model}' not found on Ollama server")
        else:
            raise HTTPException(status_code=500, detail="Error communicating with LLM")
            
    ai_text = ollama_res.get("response", "")
    
    # Determine conversation_id
    conv_id = request.conversation_id
    if not conv_id:
        max_conv = db.query(Message).filter(Message.user_id == user_id).order_by(Message.conversation_id.desc()).first()
        conv_id = (max_conv.conversation_id + 1) if max_conv and max_conv.conversation_id else 1
    
    # Store message
    msg = Message(
        user_id=user_id,
        model_used=request.model_id,
        user_message=request.message,
        ai_response=ai_text,
        conversation_id=conv_id
    )
    db.add(msg)
    
    # Increment usage
    setattr(usage, f"model_{group}_uses", current_uses + 1)
    db.commit()
    db.refresh(msg)
    
    return {
        "status": "success",
        "message_id": msg.message_id,
        "conversation_id": conv_id,
        "ai_response": ai_text,
        "model_used": request.model_id,
        "timestamp": msg.timestamp.isoformat(),
        "uses_remaining": {
            "llama2_7b_qwen2_7b": max(0, LIMITS[tier]["7b"] - usage.model_7b_uses) if tier == "free" else "unlimited",
            "llama2_14b": max(0, LIMITS[tier]["14b"] - usage.model_14b_uses),
            "llama2_32b": max(0, LIMITS[tier]["32b"] - usage.model_32b_uses)
        }
    }

@router.get("/conversations")
def get_conversations(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    
    # 30-day cleanup
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    db.query(Message).filter(Message.user_id == user_id, Message.timestamp < thirty_days_ago, Message.deleted_at == None).update({"deleted_at": datetime.utcnow()})
    db.commit()

    messages = db.query(Message).filter(Message.user_id == user_id, Message.deleted_at == None).order_by(Message.timestamp.desc()).all()
    
    convs = {}
    for m in messages:
        cid = m.conversation_id
        if cid not in convs and cid is not None:
            title = m.user_message[:30] + "..." if len(m.user_message) > 30 else m.user_message
            convs[cid] = {"conversation_id": cid, "title": title}
            
    return {"conversations": list(convs.values())}

@router.delete("/conversation/{conversation_id}")
def delete_conversation(conversation_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    messages = db.query(Message).filter(Message.user_id == user_id, Message.conversation_id == conversation_id).all()
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    for m in messages:
        m.deleted_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Conversation deleted"}

@router.get("/history")
def get_history(conversation_id: int = None, limit: int = 50, offset: int = 0, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    
    query = db.query(Message).filter(Message.user_id == user_id, Message.deleted_at == None)
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
