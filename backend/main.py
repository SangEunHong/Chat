from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from routers import user, post, comments, chat, admin_users
from database import SessionLocal, engine, Base
import models, schemas, crud
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(post.router)
app.include_router(comments.router)      # (list, create)
app.include_router(comments.standalone)   # (update, delete)
app.include_router(chat.router)
app.include_router(admin_users.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)