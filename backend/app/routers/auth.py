from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import User
from ..auth import hash_password, verify_password, create_access_token, get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterReq(BaseModel):
    """注册请求模型。"""
    username: str
    password: str
    role: str = "creator"


class LoginReq(BaseModel):
    """登录请求模型。"""
    username: str
    password: str


class TokenOut(BaseModel):
    """登录响应令牌。"""
    access_token: str
    token_type: str = "bearer"


@router.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password), role=req.role)
    db.add(user)
    db.commit()
    return {"message": "注册成功"}


@router.post("/login", response_model=TokenOut)
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.username, user.role)
    return TokenOut(access_token=token)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role}