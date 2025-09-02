from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
from rag.search import rag_answer

app = FastAPI()

class AskIn(BaseModel):
    question: str
    top_k: int | None = 8

class AskOut(BaseModel):
    answer: str

@app.post("/rag/ask", response_model=AskOut)
def ask(body: AskIn):
    print("[DEBUG] CWD =", os.getcwd())
    print("[DEBUG] Q   =", body.question)
    ans = rag_answer(body.question, top_k=body.top_k or 8)
    print("[DEBUG] A   =", ans[:200].replace('\n',' '))
    return JSONResponse(
        content={"answer": ans},
        media_type="application/json; charset=utf-8"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service:app", host="0.0.0.0", port=9001, reload=False)
