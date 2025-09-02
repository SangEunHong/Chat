from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import SessionLocal
import schemas, crud, models
from auth import get_current_user
from typing import Optional 

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 공통: 관리자 권한 체크
def require_admin(current_user: models.User = Depends(get_current_user)):
    # 탈퇴 상태면 접근 불가
    if getattr(current_user, "is_deleted", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="탈퇴된 계정입니다.")
    # role 확인 (없으면 'user'로 간주)
    role = getattr(current_user, "role", "user")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return current_user

@router.get("", response_model=schemas.AdminUserList)
def list_users(
    status: str = Query("active", pattern="^(active|deleted|all)$"),
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),  
    _: models.User = Depends(require_admin),
):
    skip = (page - 1) * size
    total, users = crud.admin_list_users(db, status=status, q=q, skip=skip, limit=size)
    return {"total": total, "items": users}

@router.patch("/{user_id}/soft-delete", response_model=schemas.AdminUserBase)
def soft_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    user = crud.admin_soft_delete_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}/restore", response_model=schemas.AdminUserBase)
def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    user = crud.admin_restore_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=204)
def hard_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    ok = crud.admin_hard_delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return

