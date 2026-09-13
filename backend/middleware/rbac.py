from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from core.config import settings

security = HTTPBearer()

def verify_role(required_roles: list):
    def role_dependency(credentials: HTTPAuthorizationCredentials = Security(security)):
        token = credentials.credentials
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            role = payload.get("role")
            if role not in required_roles:
                raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return role_dependency
