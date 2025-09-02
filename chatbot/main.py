# main.py
import argparse, sys
import requests
from crawler.web_crawler import crawl_all
from processor.cleaner import build_clean
from processor.chunker import build_chunks
from embedder.embed_faiss import build_faiss_index
from rag.search import rag_answer as _rag_answer

def ollama_alive(url="http://localhost:11434/api/tags", timeout=2):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def rag_answer(query, top_k=5, prefer_generate=True):
    # prefer_generate=True 이지만, Ollama 안 떠있으면 generate=False로 자동 우회
    gen_ok = prefer_generate and ollama_alive()
    return _rag_answer(query, top_k=top_k, generate=gen_ok)

def run_all():
    crawl_all()
    build_clean()
    build_chunks()
    build_faiss_index()
    print("✔️ 전체 파이프라인 완료!\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gen", action="store_true", help="생성 비활성화(Ollama 미사용)")
    ap.add_argument("--topk", type=int, default=5)
    args = ap.parse_args()

    run_all()

    prefer_generate = not args.no_gen
    if prefer_generate and not ollama_alive():
        print(" Ollama가 감지되지 않아 생성 없이 스니펫만 반환합니다. (--no-gen 동일)")

    while True:
        try:
            q = input("\n질문을 입력하세요 (예: 회사 미션이 뭐야?) > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.strip().lower() in ("exit", "quit", "q"):
            break
        ans = rag_answer(q, top_k=args.topk)
        print("\n[답변]\n", ans)
