from database import get_db, User, Usage, Base, engine
from datetime import date
from services.auth_service import hash_password
from routes.usage import get_remaining_uses

def test_db_operations():
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

    res = get_remaining_uses({"user_id": user.user_id, "tier": "free"}, db)
    assert res is not None
    assert "usage" in res
