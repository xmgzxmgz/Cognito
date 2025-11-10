from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET = "cognito_dev_secret"  # 可迁移至环境变量
JWT_EXPIRE_MINUTES = 120


def get_db():
    """
    获取数据库会话依赖。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    """
    生成密码哈希。

    参数:
        password: 原始密码。
    返回值:
        哈希字符串。
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    校验密码与哈希是否匹配。
    """
    return pwd_context.verify(password, hashed)


def create_access_token(username: str, role: str) -> str:
    """
    创建JWT访问令牌。

    参数:
        username: 用户名。
        role: 角色。
    返回值:
        JWT 字符串。
    """
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    FastAPI 依赖：解析与校验JWT，返回当前用户。

    参数:
        creds: 授权头部凭证。
        db: 数据库会话。
    返回值:
        User 对象。
    """
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效令牌")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="令牌缺失用户信息")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user