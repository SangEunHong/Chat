"""
comments.py
- 게시글별 댓글 CRUD API 라우터
- 댓글 목록 조회, 생성 (게시글별)
- 댓글 개별 수정, 삭제
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user  # 토큰에서 user 반환 (userID, name 포함)

router = APIRouter(prefix="/posts", tags=["comments"])

def get_post_or_404(db: Session, post_id: int): #post_id의 게시글이 존재하는지 확인
    post = db.query(models.Post).filter(models.Post.post_id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    return post

@router.get("/{post_id}/comments", response_model=list[schemas.CommentOut]) #특정 게시글의 댓글 목록 조회
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    get_post_or_404(db, post_id)
    q = (db.query(models.Comment)
           .filter(models.Comment.post_id == post_id)
           .order_by(models.Comment.created_at.asc()))
    return q.offset((page-1)*size).limit(size).all()

@router.post("/{post_id}/comments", response_model=schemas.CommentOut, status_code=201)
def create_comment(
    post_id: int,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    get_post_or_404(db, post_id)
    c = models.Comment(
        post_id=post_id,
        user_id=current_user.userID,
        author_name=current_user.name,
        content=payload.content.strip(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

# 개별 수정/삭제
standalone = APIRouter(prefix="/comments", tags=["comments"])

##주어진 comment_id의 댓글이 존재하는지 확인
def get_comment_or_404(db: Session, comment_id: int):
    c = db.query(models.Comment).filter(models.Comment.comment_id == comment_id).first()
    if not c:
        raise HTTPException(404, "Comment not found")
    return c
#댓글 수정(본인이 작성한것만)
@standalone.put("/{comment_id}", response_model=schemas.CommentOut)
def update_comment(
    comment_id: int,
    payload: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    c = get_comment_or_404(db, comment_id)
    if c.user_id != current_user.userID:
        raise HTTPException(403, "Forbidden")
    c.content = payload.content.strip()
    db.commit()
    db.refresh(c)
    return c
#댓글 삭제(본인이 한것만)
@standalone.delete("/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    c = get_comment_or_404(db, comment_id)
    if c.user_id != current_user.userID:
        raise HTTPException(403, "Forbidden")
    db.delete(c)
    db.commit()
    return