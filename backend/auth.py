"""
auth.py
- 비밀번호 해시/검증
- JWT 토큰 생성 및 검증
- 현재 로그인 사용자 조회 의존성
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from dotenv import load_dotenv
from passlib.context import CryptContext 
import os

from database import get_db
import models

# 환경 변수 로드 및 기본 설정
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")  # 환경변수 없을 경우 기본값 사용
ALGORITHM = "HS256" # JWT 알고리즘
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# FastAPI용 Bearer 인증 스키마
security = HTTPBearer()

# bcrypt 기반 비밀번호 해시 Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호 해시 생성
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 비밀번호 검증
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT 토큰 검증
def verify_token(credentials=Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

# 현재 로그인 사용자 조회
def get_current_user(payload=Depends(verify_token), db: Session = Depends(get_db)):
    """
    토큰 payload에서 사용자 식별자를 꺼내 DB로 검증 후 User 객체 반환.
    - 우선순위: sub → userID
    """
    user_id = payload.get("sub") or payload.get("userID")
    print("Decoded claims:", payload)
    if user_id is None:
        raise HTTPException(status_code=401, detail="토큰에 사용자 정보가 없습니다.", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="토큰의 사용자 정보가 올바르지 않습니다.", headers={"WWW-Authenticate": "Bearer"})
    # DB에서 사용자 조회
    user = db.query(models.User).filter(models.User.userID == user_id_int).first()
    print("Decoded claims:", payload)
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.", headers={"WWW-Authenticate": "Bearer"})
    return user