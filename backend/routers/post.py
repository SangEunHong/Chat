"""
posts.py
- 게시글 CRUD API 라우터
- 게시글 생성, 전체 조회, 단일 조회, 수정, 삭제 기능 제공
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
from auth import verify_token
import schemas, crud, models
from typing import List

router = APIRouter()

# 유틸: 토큰에서 사용자 찾기 (sub가 int(userID)든 str(로그인ID)든 처리)
def _resolve_user(db: Session, token_data: dict) -> models.User:
    sub = token_data.get("sub") or token_data.get("userID")
    if sub is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    # 정수 또는 숫자 문자열 → userID로 조회
    if isinstance(sub, int) or (isinstance(sub, str) and sub.isdigit()):
        user = db.query(models.User).filter(models.User.userID == int(sub)).first()
    else:
        # 문자열 → 로그인 ID로 조회
        user = crud.get_user_by_id(db, sub)  # 네 프로젝트에서 'ID'(로그인 ID)로 조회
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user

# 게시글 생성
@router.post("/posts", response_model=schemas.PostResponse)
def create_post(
    post_data: schemas.PostCreate = Body(...),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user = _resolve_user(db, token_data)
    new_post = crud.create_post(db, post_data, user.userID)
    return {
        "post_id": new_post.post_id,
        "title": new_post.title,
        "content": new_post.content,
        "created_at": new_post.created_at,
        "user_id": user.userID,
        "author_name": user.name,
    }

# 전체 게시글 조회
@router.get("/posts", response_model=List[schemas.PostListResponse])
def get_posts(db: Session = Depends(get_db)):
    # crud.get_all_posts는 dict 리스트를 반환하도록 유지 (네 crud 최신본 기준 OK)
    return crud.get_all_posts(db)

# 게시글 상세 조회
@router.get("/posts/{post_id}", response_model=schemas.PostListResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(
            models.Post.post_id,
            models.Post.title,
            models.Post.content,
            models.Post.created_at,
            models.Post.user_id.label("user_id"),     # ✅ 라벨 통일 중요
            models.User.name.label("author_name"),
        )
        .join(models.User, models.User.userID == models.Post.user_id)
        .filter(models.Post.post_id == post_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    # 스키마에 from_attributes=True를 넣었으니 row 그대로 리턴해도 되지만,
    # 더 안전하게 dict로 반환
    return {
        "post_id": row.post_id,
        "title": row.title,
        "content": row.content,
        "created_at": row.created_at,
        "user_id": row.user_id,
        "author_name": row.author_name,
    }

# 게시글 삭제
@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user = _resolve_user(db, token_data)

    # 엔티티 로드
    post = db.query(models.Post).filter(models.Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    # 🔐 권한 체크: 관리자면 통과, 아니면 본인 글만
    role = getattr(user, "role", "user")
    if role != "admin" and post.user_id != user.userID:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

    db.delete(post)
    db.commit()
    return {"ok": True}

# 게시글 수정
@router.put("/posts/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int,
    payload: schemas.PostUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user = _resolve_user(db, token_data)

    post = db.query(models.Post).filter(models.Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    if post.user_id != user.userID:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    post.title = payload.title
    post.content = payload.content
    db.commit()
    db.refresh(post)

    return {
        "post_id": post.post_id,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "user_id": post.user_id,
        "author_name": user.name,
    }