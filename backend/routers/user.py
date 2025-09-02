"""
users.py
- 회원가입, 로그인, 아이디/비밀번호 찾기, 마이페이지 조회·수정·탈퇴 등 사용자 계정 관련 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import schemas, crud, models
from database import get_db
from auth import verify_password, create_access_token, verify_token, hash_password, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from schemas import DeleteUserRequest
from datetime import datetime, timedelta

router = APIRouter()
RESET_TOKEN_EXPIRE_MINUTES = 10

# 회원가입
@router.post("/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, user.ID)
    if db_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 ID입니다.")
    return crud.create_user(db, user)

# ID 중복 확인
@router.get("/check-id")
def check_user_id(ID: str, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, ID)
    return {"available": db_user is None}

# 로그인
@router.post("/login")
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_id(db, login_data.ID)
    if not db_user or not verify_password(login_data.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID 또는 비밀번호가 올바르지 않습니다."
        )
    print("LOGIN OK:", db_user.userID, db_user.ID, db_user.role)

    # sub 은 userID(정수)를 문자열로 저장
    access_token = create_access_token(
        data={"sub": str(db_user.userID), "role": db_user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "name": db_user.name,
        "userID": db_user.userID,
        "role": db_user.role,
    }

# 아이디 찾기
@router.post("/find-id", response_model=schemas.FindIdResponse)
def find_id(payload: schemas.FindIdRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_name_phone(db, name=payload.name, phone=payload.phone)
    if not user:
        raise HTTPException(status_code=404, detail="일치하는 정보가 없습니다.")
    return schemas.FindIdResponse(ID=user.ID)

# --- 비밀번호 재설정 시작 ---
@router.post("/password/reset-start", response_model=schemas.PasswordResetStartResponse)
def password_reset_start(body: schemas.PasswordResetStartRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_id_name_phone(db, ID=body.ID, name=body.name, phone=body.phone)
    if not user:
        raise HTTPException(status_code=404, detail="입력한 정보와 일치하는 사용자가 없습니다.")
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    reset_claims = {
        "sub": user.ID,
        "typ": "pwd_reset",
        "exp": expire,
        "iat": datetime.utcnow().timestamp(),
    }
    reset_token = jwt.encode(reset_claims, SECRET_KEY, algorithm=ALGORITHM)
    return schemas.PasswordResetStartResponse(reset_token=reset_token)

# --- 비밀번호 재설정 확정 ---
@router.post("/password/reset-confirm")
def password_reset_confirm(body: schemas.PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(body.reset_token, SECRET_KEY, algorithms=[ALGORITHM])
        if claims.get("typ") != "pwd_reset":
            raise HTTPException(status_code=400, detail="유효하지 않은 토큰 유형입니다.")
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="토큰에 사용자 정보가 없습니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")

    user = crud.get_user_by_id(db, user_id_str)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    hashed = hash_password(body.new_password)
    crud.update_user_password(db, user, hashed)
    return {"msg": "비밀번호가 변경되었습니다."}

# 토큰 유효성 검사
@router.get("/verify-token")
def verify_user_token(token: str = Depends(verify_token)):
    return {"valid": True}

# ===== 마이페이지 =====
def _find_user_by_token_sub(db: Session, sub: str | int):
    """
    sub 가 숫자(userID)면 userID로, 아니면 로그인 ID로 조회
    """
    if isinstance(sub, int):
        return db.query(models.User).filter(models.User.userID == sub).first()
    if isinstance(sub, str) and sub.isdigit():
        return db.query(models.User).filter(models.User.userID == int(sub)).first()
    return crud.get_user_by_id(db, sub)

# 조회 (alias: /users/mypage 도 허용)
@router.get("/mypage", response_model=schemas.UserResponse)
@router.get("/users/mypage", response_model=schemas.UserResponse)
def get_my_page(payload: dict = Depends(verify_token), db: Session = Depends(get_db)):
    sub = payload.get("sub")
    user = _find_user_by_token_sub(db, sub)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user

# 수정 (alias 포함)
@router.put("/mypage/update", response_model=schemas.UserResponse)
@router.put("/users/mypage/update", response_model=schemas.UserResponse)
def update_my_page(update_data: schemas.UserUpdate, payload: dict = Depends(verify_token), db: Session = Depends(get_db)):
    sub = payload.get("sub")
    user = _find_user_by_token_sub(db, sub)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return crud.update_user(db, user, update_data)

# 탈퇴 (alias 포함)
@router.delete("/mypage/delete")
@router.delete("/users/mypage/delete")
def delete_account(
    data: DeleteUserRequest,
    db: Session = Depends(get_db),
    token_data: dict = Depends(verify_token)
):
    user = _find_user_by_token_sub(db, token_data.get("sub"))
    if user is None:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
    crud.delete_user(db, user)
    return {"msg": "회원 탈퇴가 완료되었습니다."}
