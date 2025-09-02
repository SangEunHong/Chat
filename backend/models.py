from datetime import datetime
from sqlalchemy import Column, Integer, String,  Boolean, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

# User 모델 (회원 테이블)
class User(Base):
    __tablename__ = "users"

    userID = Column(Integer, primary_key=True, autoincrement=True)
    ID = Column(String(30), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(7), nullable=False)
    bdate = Column(Date, nullable=False)
    phone = Column(String(15), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # 관리자/일반 구분
    role = Column(String(10), nullable=False, server_default="user")  # "user" | "admin"

    # 소프트 삭제 필드 (탈퇴)
    is_deleted = Column(Boolean, nullable=False, server_default="0", index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    # 관계: User → Post (1:N)
    posts = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",           # 유저 삭제 시 게시글도 삭제
        passive_deletes=True,
    )
    # 관계: User → Comment (1:N)
    comments = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",           # 유저 삭제 시 댓글도 삭제
        passive_deletes=True,
    )

# Post 모델 (게시글 테이블)    
class Post(Base):
    __tablename__ = "posts"

    post_id = Column(Integer, primary_key=True, index=True)  # post_id가 PK
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ⚠️ DB에는 컬럼명이 id 이지만, 파이썬 속성은 user_id 로 사용하고 싶다면 아래처럼 매핑
    user_id = Column(
        Integer,
        ForeignKey("users.userID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 관계: Post → User (N:1)
    author = relationship("User", back_populates="posts")
    # 관계: Post → Comment (1:N)
    comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",  # 게시글 삭제 시 댓글도 삭제
        passive_deletes=True,
    )

# Comment 모델 (댓글 테이블)
class Comment(Base):
    __tablename__ = "comments"


    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.post_id", ondelete="CASCADE"),  # ✅ 대상 칼럼명 수정 + CASCADE
        index=True,
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.userID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_name = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),  # 수정 시 자동 갱신
        nullable=False,
    )

    # 관계: Comment → Post (N:1)
    post = relationship("Post", back_populates="comments")
    #관계: Comment → User (N:1)
    author = relationship("User", back_populates="comments")

class ChatThread(Base):
    __tablename__ = "chat_threads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)   # 로그인 연동 시 외래키로 바꿔도 됨
    title = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("chat_threads.id"), index=True)
    role = Column(Text, nullable=False)        # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("ChatThread", back_populates="messages")