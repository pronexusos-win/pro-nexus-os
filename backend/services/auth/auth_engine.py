from datetime import datetime, timedelta
import jwt
import bcrypt
from core.config import settings

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    # bcrypt ต้องการข้อมูลเป็น bytes เลยต้อง .encode('utf-8') ก่อน
    return bcrypt.checkpw(plain_pin.encode('utf-8'), hashed_pin.encode('utf-8'))

def get_pin_hash(pin: str) -> str:
    # เข้ารหัสแล้วแปลงกลับเป็น string เพื่อเก็บลงฐานข้อมูล
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=12)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt
