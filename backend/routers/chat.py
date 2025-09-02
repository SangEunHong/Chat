# routers/chat.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import schemas, crud
import httpx  # ← 추가

router = APIRouter(prefix="/api/chat", tags=["chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

RAG_URL = "http://127.0.0.1:9001/rag/ask"

def call_rag(question: str, top_k: int = 8) -> str:
    try:
        # proxies 제거, trust_env=False만 사용
        with httpx.Client(timeout=300.0, trust_env=False) as client:
            resp = client.post(RAG_URL, json={"question": question, "top_k": top_k})
            resp.raise_for_status()
            return resp.json().get("answer", "(빈 응답)")
    except Exception as e:
        return f"[RAG 호출 실패] {e}"

# ---- 채팅 단발 응답 ----
@router.post("", response_model=schemas.ChatOut)
def chat(body: schemas.ChatIn, db: Session = Depends(get_db)):
    thread_id = body.thread_id or crud.create_chat_thread(db, user_id=None)

    # 👉 RAG 호출로 답변 생성
    reply = call_rag(body.message, top_k=8)

    # 로그 기록
    crud.create_chat_message(db, thread_id, "user", body.message)
    crud.create_chat_message(db, thread_id, "assistant", reply)

    return {"reply": reply, "thread_id": thread_id}
