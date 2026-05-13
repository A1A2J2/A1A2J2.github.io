from database import get_db, User, Usage, Base, engine
from datetime import date
from services.auth_service import hash_password
from routes.usage import get_remaining_uses

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = next(get_db())

# Create test user
user = db.query(User).filter(User.username == "testuser99").first()
if not user:
    user = User(username="testuser99", password_hash=hash_password("pwd"), email="test99@test.com", tier="free")
    db.add(user)
    db.commit()
    db.refresh(user)

    usage = Usage(user_id=user.user_id, month_start_date=date.today())
    db.add(usage)
    db.commit()

try:
    res = get_remaining_uses({"user_id": user.user_id, "tier": "free"}, db)
    print("SUCCESS", res)
except Exception as e:
    import traceback
    traceback.print_exc()

