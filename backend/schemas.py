from pydantic import BaseModel, validator, constr, Field, ConfigDict
from datetime import date, datetime
import re
from typing import Optional, List

#회원 관련
class AdminUserBase(BaseModel):
    userID: int
    ID: str                 # 로그인 ID
    name: str
    phone: str
    bdate: date
    role: str               # "user" | "admin"
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2

class AdminUserList(BaseModel):
    total: int
    items: List[AdminUserBase]

# 회원가입 요청 (사용자 입력 데이터)
class UserCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ID: str = Field(alias="id")
    password: str
    name: str
    bdate: date
    phone: str

    # 비밀번호 유효성 검사
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("비밀번호에는 최소 하나의 특수문자가 포함되어야 합니다.")
        return v
    
    # 이름: 한글만 허용
    @validator("name")
    def validate_name(cls, v):
        if not re.fullmatch(r"[가-힣]+", v):
            raise ValueError("이름은 한글만 입력 가능합니다.")
        return v
    
    # 휴대폰 번호 형식 검사
    @validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^010-\d{4}-\d{4}$", v):
            raise ValueError("휴대폰 번호는 010-XXXX-XXXX 형식이어야 합니다.")
        return v

# 회원정보 수정 요청 (선택적 필드)
class UserUpdate(BaseModel):
    password: Optional[str] = None
    name: Optional[str] = None
    bdate: Optional[date] = None
    phone: Optional[str] = None

    @validator("password") #@field_validator
    def validate_password(cls, v):
        if v and (len(v) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v)):
            raise ValueError("비밀번호는 특수문자 포함 8자리 이상이어야 합니다.")
        return v

    @validator("name")
    def validate_name(cls, v):
        if v and not re.fullmatch(r"[가-힣]+", v):
            raise ValueError("이름은 한글만 입력 가능합니다.")
        return v

    @validator("phone")
    def validate_phone(cls, v):
        if v and not re.match(r"^010-\d{4}-\d{4}$", v):
            raise ValueError("휴대폰 번호는 010-XXXX-XXXX 형식이어야 합니다.")
        return v
    
# 회원 탈퇴 요청
class DeleteUserRequest(BaseModel):
    password: str

# 회원정보 응답 (비밀번호 제외)
class UserResponse(BaseModel): 
    userID: int
    ID: str
    name: str
    bdate: date
    phone: str

    class Config:
        from_attributes = True

#인증 / 로그인
class LoginRequest(BaseModel): 
    ID: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None

#게시글 관련
class PostCreate(BaseModel):
    title: str
    content: str


class PostResponse(BaseModel):
    post_id: int  # models.Post의 PK 필드명과 동일하게
    title: str
    content: str
    created_at: datetime
    user_id: int                 
    author_name: str 

    class Config:
        from_attributes = True  # Pydantic v2 방식

class PostListResponse(BaseModel):
    post_id: int
    title: str
    content: str
    created_at: datetime
    user_id: int
    author_name: str

    class Config:
        from_attributes = True
    
class PostUpdate(BaseModel):
    title: str
    content: str

#댓글 관련
class CommentBase(BaseModel):
    content: constr(min_length=1, max_length=2000)

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: constr(min_length=1, max_length=2000)

class CommentOut(BaseModel):
    comment_id: int
    post_id: int
    user_id: int
    author_name: str
    content: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# 아이디 찾기 / 비밀번호 재설정

# 아이디 찾기 요청
class FindIdRequest(BaseModel):
    name: str
    phone: str
# 아이디 찾기 응답
class FindIdResponse(BaseModel):
    ID: str

# 비밀번호 재설정 시작 요청 (본인확인)
class PasswordResetStartRequest(BaseModel):
    ID: str
    name: str
    phone: str

# 비밀번호 재설정 확정 요청
class PasswordResetStartResponse(BaseModel):
    reset_token: str

class PasswordResetConfirmRequest(BaseModel):
    reset_token: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("비밀번호에는 최소 하나의 특수문자가 포함되어야 합니다.")
        return v
    
class ChatIn(BaseModel):
    message: str
    thread_id: Optional[int] = None

class ChatOut(BaseModel):
    reply: str
    thread_id: int

class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True   # Pydantic v2

class ChatThreadRead(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True