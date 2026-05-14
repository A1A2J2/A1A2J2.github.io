from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db, Memory
from models import MemoryUpdate
from middleware.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_memories(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    memories = db.query(Memory).filter(Memory.user_id == user_id).order_by(Memory.created_at.desc()).all()
    return {"memories": [{"memory_id": m.memory_id, "content": m.content, "created_at": m.created_at.isoformat()} for m in memories]}

@router.put("/{memory_id}")
def update_memory(memory_id: int, req: MemoryUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    memory = db.query(Memory).filter(Memory.memory_id == memory_id, Memory.user_id == user_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    memory.content = req.content
    db.commit()
    db.refresh(memory)
    return {"status": "success", "memory": {"memory_id": memory.memory_id, "content": memory.content}}

@router.delete("/{memory_id}")
def delete_memory(memory_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user["user_id"]
    memory = db.query(Memory).filter(Memory.memory_id == memory_id, Memory.user_id == user_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(memory)
    db.commit()
    return {"status": "success", "message": "Memory deleted"}
