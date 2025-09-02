from sqlalchemy.orm import Session
import models, schemas
from auth import hash_password
from models import Post
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import models

def admin_list_users(
    db: Session,
    status: str = "active",   # "active" | "deleted" | "all"
    q: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(models.User)
    if status == "active":
        query = query.filter(models.User.is_deleted == False)
    elif status == "deleted":
        query = query.filter(models.User.is_deleted == True)
    # status == "all"이면 필터 없음

    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.User.ID.ilike(like),
                                 models.User.name.ilike(like),
                                 models.User.phone.ilike(like)))

    total = query.count()
    users = query.order_by(models.User.userID.desc()).offset(skip).limit(limit).all()
    return total, users

def admin_soft_delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.userID == user_id).first()
    if not user:
        return None
    if user.is_deleted:
        return user
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def admin_restore_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.userID == user_id).first()
    if not user:
        return None
    if not user.is_deleted:
        return user
    user.is_deleted = False
    user.deleted_at = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def admin_hard_delete_user(db: Session, user_id: int) -> bool:
    user = db.query(models.User).filter(models.User.userID == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True

def admin_purge_expired_deleted_users(db: Session, days: int = 365) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = (db.query(models.User)
           .filter(and_(models.User.is_deleted == True,
                        models.User.deleted_at < cutoff)))
    users = q.all()
    count = 0
    for u in users:
        db.delete(u)
        count += 1
    db.commit()
    return count

#  사용자(User) 관련 CRUD
#로그인 ID(문자열)로 사용자 조회
def get_user_by_id(db: Session, user_id: str): 
    return db.query(models.User).filter(models.User.ID == user_id).first()

#새 사용자 생성
def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        ID=user.ID,
        password=hash_password(user.password),
        name=user.name,
        bdate=user.bdate,
        phone=user.phone
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

#사용자 정보 수정
def update_user(db: Session, db_user: models.User, update_data: schemas.UserUpdate):
    if update_data.name is not None:
        db_user.name = update_data.name
    if update_data.bdate is not None:
        db_user.bdate = update_data.bdate
    if update_data.phone is not None:
        db_user.phone = update_data.phone
    if update_data.password is not None:
        db_user.password = hash_password(update_data.password)

    db.commit()
    db.refresh(db_user)
    return db_user

#사용자 계정 삭제
def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()

#이름+전화번호로 사용자 조회->아이디 찾기
def get_user_by_name_phone(db: Session, name: str, phone: str):
    return db.query(models.User).filter(
        models.User.name == name,
        models.User.phone == phone
    ).first()

#아이디+이름+비밀번호로 사용자 조회-> 비밀번호 재설정
def get_user_by_id_name_phone(db: Session, ID: str, name: str, phone: str):
    return db.query(models.User).filter(
        models.User.ID == ID,
        models.User.name == name,
        models.User.phone == phone
    ).first()

#비밀번호 업데이트
def update_user_password(db: Session, user: models.User, new_hashed_password: str):
    user.password = new_hashed_password
    db.commit()
    db.refresh(user)
    return user       

#게시글(pot) 관련 crud
#새 게시글 생성
def create_post(db: Session, post_data: schemas.PostCreate, user_id: int):
    post = Post(
        title=post_data.title,
        content=post_data.content,
        user_id=user_id
    )

    db.add(post)
    db.commit()
    db.refresh(post)
    return post
#전체 게시글 목록 조회(최신 작성순)
def get_all_posts(db: Session):
    rows = (
        db.query(
            models.Post.post_id,
            models.Post.title,
            models.Post.content,
            models.Post.created_at,
            models.User.userID.label("user_id"),
            models.User.name.label("author_name"),
        )
        .join(models.User, models.Post.user_id == models.User.userID)
        .order_by(models.Post.created_at.desc())
        .all()
    )
    # Row -> dict 변환
    return [
        {
            "post_id": r.post_id,
            "title": r.title,
            "content": r.content,
            "created_at": r.created_at,
            "user_id": r.user_id,
            "author_name": r.author_name,
        }
        for r in rows
    ]
#게시글 상세 조회
def get_post_by_id(db: Session, post_id: int):
    return (
        db.query(
            models.Post.post_id,
            models.Post.title,
            models.Post.content,
            models.Post.created_at,
            models.Post.user_id,
            models.User.name.label("author_name"),
        )
        .join(models.User, models.User.userID == models.Post.user_id)
        .filter(models.Post.post_id == post_id)
        .first()
    )    
#게시글 삭제
def delete_post(db: Session, post: models.Post):
    db.delete(post)
    db.commit()

def create_chat_thread(db: Session, user_id: int | None = None, title: str | None = None) -> int:
    thread = models.ChatThread(user_id=user_id, title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread.id

def create_chat_message(db: Session, thread_id: int, role: str, content: str) -> models.ChatMessage:
    msg = models.ChatMessage(thread_id=thread_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_thread_messages(db: Session, thread_id: int) -> list[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
          .filter(models.ChatMessage.thread_id == thread_id)
          .order_by(models.ChatMessage.id.asc())
          .all()
    )