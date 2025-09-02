# embedder/embed_faiss.py
# -----------------------------------------------------------------------------
# 역할:
#   - chunks.jsonl(청크 파일)을 읽어 문장 임베딩을 만든 뒤
#     FAISS(IndexFlatIP) 인덱스를 생성/저장하고,
#     질의 시 동일한 순서로 역매핑할 수 있도록 texts/metas도 JSONL로 저장.
#
# 핵심 포인트:
#   1) SentenceTransformer 로 임베딩 생성 (normalize_embeddings=True)
#      → 코사인 유사도를 Inner Product(IP)로 사용 가능
#   2) FAISS IndexFlatIP 사용
#      → GPU 없이도 빠른 벡터 검색이 가능, 파라미터가 없어 디버깅 용이
#   3) texts/metas 는 "벡터 순서와 1:1" 로 저장 (매우 중요)
#      → 검색 결과의 인덱스(i)로 원문/메타를 바로 조회하기 위해서
# -----------------------------------------------------------------------------
import json, os, sys
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss

from config import (
    CHUNKS_PATH, INDEX_DIR, FAISS_INDEX, FAISS_TEXTS, FAISS_METAS, EMBED_MODEL_NAME
)

# CPU 기준 적당한 배치(너무 크면 메모리/속도 손해, 너무 작으면 오버헤드↑)
BATCH_SIZE = 8  # CPU면 8~16 권장, GPU면 32~128까지도 가능

def _atomic_write_lines(path: Path, lines_iter):
    """
    JSONL을 '원자적'으로 저장.
    - 임시 파일에 먼저 쓴 뒤 os.replace로 교체 → 저장 도중 중단돼도 원본이 깨지지 않음.
    - texts/metas는 검색 정확도에 직결되므로, 중간 실패로 파일이 망가지지 않게 주의.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in lines_iter:
            f.write(row + "\n")
    os.replace(tmp, path)

def build_faiss_index():
    # 출력 디렉터리 준비
    Path(INDEX_DIR).mkdir(parents=True, exist_ok=True)

    # SentenceTransformer는 CPU/GPU 모두 지원.
    # 여기서는 배포 간단화를 위해 CPU 고정(Windows 서버 호환성↑).
    device = "cpu"
    print(f"[DEBUG] device={device}, model={EMBED_MODEL_NAME}")

    # 모델 경로가 로컬 디렉터리라면 내부 파일 목록 찍어 디버깅에 도움
    if os.path.isdir(EMBED_MODEL_NAME):
        try:
            print("[DEBUG] model dir files:", os.listdir(EMBED_MODEL_NAME))
        except Exception:
            pass

    # 1) 임베딩 모델 로드
    #    - BAAI/bge-m3 같은 멀티벡터 모델도 SentenceTransformer 호환
    model = SentenceTransformer(EMBED_MODEL_NAME, device=device)

    # 2) 입력 청크 로드
    #    - 텍스트가 비어있는 레코드는 스킵
    #    - meta에서 검색에 유용한 필드만 추려 저장(원문 meta는 CHUNKS_PATH에 남아있음)
    texts, metas = [], []
    n_in, n_skip = 0, 0
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        for line in tqdm(f, desc="임베딩 입력 로드"):
            n_in += 1
            rec = json.loads(line)
            txt = (rec.get("text") or "").strip()
            if not txt:
                n_skip += 1
                continue
            meta = rec.get("meta", {}) or {}
            texts.append(txt)
            metas.append({
                "id": rec.get("id"),
                "url": meta.get("url"),
                "title": meta.get("title"),
                "section": meta.get("section"),
                "name": meta.get("name"),
                "type": meta.get("type"),
            })

    if not texts:
        # 청크가 비었으면 이후 단계가 모두 무의미 → 즉시 실패 처리
        raise RuntimeError(f"CHUNKS 비었음: {CHUNKS_PATH}")

    # 3) 임베딩 계산
    #    - normalize_embeddings=True → 각 벡터를 L2 정규화
    #      코사인유사도(a·b / |a||b|) = 정규화 후 내적(a'·b')와 동일 → IndexFlatIP로 검색
    print(f"[DEBUG] encode start: n={len(texts)}/{n_in} (skip={n_skip}), batch={BATCH_SIZE}, normalize=True")
    vecs = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # ← 코사인 유사도를 Inner Product로 사용
    )

    # numpy 배열 보장
    if not isinstance(vecs, np.ndarray):
        vecs = np.asarray(vecs)

    # 4) FAISS는 float32를 권장 (float16/64 사용 시 에러/성능 저하 가능)
    if vecs.dtype != np.float32:
        vecs = vecs.astype(np.float32, copy=False)

    print(f"[DEBUG] encode done: shape={vecs.shape}, dtype={vecs.dtype}")

    # 5) FAISS 인덱스 생성/저장
    #    - IndexFlatIP: 파라미터 없는 브루트포스 IP 인덱스(정확하지만 큰 데이터셋은 느릴 수 있음)
    #    - 대규모로 가면 IVF/HNSW 등으로 교체 가능(학습 필요), 지금은 디버깅/정확성 우선
    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)  # 벡터 추가
    faiss.write_index(index, str(FAISS_INDEX))
    print(f"[DEBUG] faiss index written: {FAISS_INDEX} (ntotal={index.ntotal})")

    # 6) texts / metas 저장
    #    - "반드시" 벡터 순서와 동일하게 기록해야 search 시 역매핑이 맞아떨어짐.
    _atomic_write_lines(Path(FAISS_TEXTS), (json.dumps(t, ensure_ascii=False) for t in texts))
    _atomic_write_lines(Path(FAISS_METAS), (json.dumps(m, ensure_ascii=False) for m in metas))

    print(f"✅ [임베딩] index/texts/metas 저장 완료")
    print(f"    - index: {FAISS_INDEX}")
    print(f"    - texts: {FAISS_TEXTS}")
    print(f"    - metas: {FAISS_METAS}")

if __name__ == "__main__":
    # CLI 실행 시 예외를 stderr로도 출력하여 CI/배치 로그에서 쉽게 발견 가능
    try:
        build_faiss_index()
    except Exception as e:
        print(f"[ERROR] build_faiss_index 실패: {e}", file=sys.stderr)
        raise