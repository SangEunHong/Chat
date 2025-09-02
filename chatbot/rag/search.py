# search.py
# -----------------------------------------------------------------------------
# 역할:
#   - 질의(query)를 받아 FAISS 벡터 검색을 수행하고,
#     회사 정보(info) / 연혁(history) / 솔루션 / 비즈니스 / 슬로건 등
#     구조화된 데이터를 조건부로 뽑아주는 RAG 검색 로직
#
# 구성:
#   1) 유틸 함수 (_norm, _load_all, _get_field_hits, _history_map, _mmr 등)
#   2) search() → 벡터 검색 + MMR 재랭크
#   3) rag_answer() → 검색결과를 유형별로 해석해 "최종 답변" 반환
# -----------------------------------------------------------------------------
import json, re, numpy as np, faiss
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
from config import FAISS_INDEX, FAISS_TEXTS, FAISS_METAS, EMBED_MODEL_NAME
# --- util ---------------------------------------------------
def _norm(s: str) -> str:
    """문자열 전처리: 공백 정리/strip → 검색 일관성 향상"""
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _load_all() -> Tuple[faiss.Index, List[str], List[Dict]]:
    """
    저장된 인덱스/텍스트/메타 로드
    - index: FAISS 인덱스
    - texts: 각 벡터에 대응하는 원문 텍스트
    - metas: 각 벡터에 대응하는 메타데이터
    """
    index = faiss.read_index(str(FAISS_INDEX))
    with open(FAISS_TEXTS, encoding="utf-8") as f:
        texts = [json.loads(l) for l in f]
    with open(FAISS_METAS, encoding="utf-8") as f:
        metas = [json.loads(l) for l in f]
    return index, texts, metas

def _get_field_hits(metas: List[Dict], texts: List[str]) -> Dict[str, str]:
    """
    info 섹션(회사명, 설립연도, 대표 등)만 뽑아 {id: text} 매핑 생성
    - rag_answer에서 '회사명?', '대표이사?' 같은 질문에 직답 용도
    """
    out = {}
    for i, m in enumerate(metas):
        sec = (m.get("meta", {}) or {}).get("section") or m.get("section")
        _id = m.get("id") or (m.get("meta", {}) or {}).get("id")
        if sec == "info" and _id and isinstance(texts[i], str):
            out[_id] = texts[i]
    return out
_TAIL_RE = re.compile(
    r"\s*(?:T\s*[.:]|Tel|전화|F\s*[.:]|팩스|지도\s*바로가기|바로가기|아이콘|본사|지사|서울\s*지사)\b.*$",
    re.I
)
def _strip_tail_from_addr(s: str) -> str:
    s = _TAIL_RE.sub("", s or "").strip()
    s = re.sub(r"\s{2,}", " ", s)
    return s

def _collect_names(metas: List[Dict], section_name: str) -> List[str]:
    """solution / business 섹션에서 name 목록만 추출"""
    names = set()
    for m in metas:
        sec = (m.get("meta", {}) or {}).get("section") or m.get("section")
        if sec != section_name:
            continue
        name = (m.get("meta", {}) or {}).get("name") or m.get("name")
        if name:
            names.add(str(name))
    return sorted(names)

def _get_by_id(metas: List[Dict], texts: List[str], target_id: str) -> str:
    """특정 id에 해당하는 텍스트 찾기"""
    for i, m in enumerate(metas):
        mid = m.get("id")
        if mid == target_id and isinstance(texts[i], str):
            return texts[i]
    return ""

def _is_company_intro_query(q: str) -> bool:
    """질문이 '이 회사가 어떤 회사냐?' 계열인지 판별"""
    q = _norm(q).lower()
    triggers = [
        "어떤 회사", "무슨 회사", "어떤 기업", "회사 소개", "회사소개",
        "회사에 대해", "회사 설명", "회사 정체성", "브랜드 슬로건",
        "범일정보는", "범일정보 어떤", "범일정보 소개"
    ]
    return any(t in q for t in triggers)

def _history_map(metas: List[Dict], texts: List[str]) -> Dict[str, List[str]]:
    """
    연혁(year -> [lines]) 맵핑
    - meta.section == 'history' and meta.year 값 기준
    - 없으면 id=연혁_YYYY에서 보조 추출
    """
    out: Dict[str, List[str]] = {}
    for i, m in enumerate(metas):
        sec = (m.get("meta", {}) or {}).get("section") or m.get("section")
        if sec != "history":
            continue
        year = (m.get("meta", {}) or {}).get("year")
        if not year:
            mid = m.get("id") or ""
            mm = re.search(r"연혁_(\d{4})", mid)
            year = mm.group(1) if mm else None
        if not year:
            continue
        out.setdefault(str(year), []).append(texts[i])
    return out

def _mmr(query_vec: np.ndarray, doc_vecs: np.ndarray, k: int, lam: float = 0.5) -> List[int]:
    """
    MMR(Maximal Marginal Relevance) 재랭크
    - 질의와 유사(s1)하면서도 기존 선택과 중복(s2)이 적은 문서를 고름
    - lam=0.5 → 유사도/다양성 균형
    """
    selected, candidates = [], list(range(len(doc_vecs)))
    sims = (doc_vecs @ query_vec.reshape(-1, 1)).ravel()
    if len(candidates) == 0:
        return selected

    # 1순위: 가장 유사한 문서
    first = int(np.argmax(sims))
    selected.append(first)
    candidates.remove(first)

    # 이후: lam * 유사도 - (1-lam) * 중복성
    while len(selected) < min(k, len(doc_vecs)) and candidates:
        max_score, max_idx = -1e9, candidates[0]
        for j in candidates:
            s1 = sims[j]
            s2 = max((doc_vecs[j] @ doc_vecs[i] for i in selected), default=0.0)
            score = lam * s1 - (1 - lam) * s2
            if score > max_score:
                max_score, max_idx = score, j
        selected.append(max_idx)
        candidates.remove(max_idx)
    return selected
# -------- 주소/연락처 정리 유틸 (NEW) ---------------------------------------
_PHONE_RE = re.compile(r"(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})")
_TEL_RE   = re.compile(r"(?:T\.|Tel|전화)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", re.I)
_FAX_RE   = re.compile(r"(?:F\.|팩스)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", re.I)

def _extract_tel_fax(s: str):
    tel = None; fax = None
    mt = _TEL_RE.search(s or "");  mf = _FAX_RE.search(s or "")
    if mt: tel = mt.group(1)
    if mf: fax = mf.group(1)
    if not tel:
        m = _PHONE_RE.search(s or "")
        if m: tel = m.group(1)
    return tel, fax

def _format_addr_line(label: str, addr: str, tel: str|None, fax: str|None):
    parts = [f"{label}: {addr}"]
    if tel: parts.append(f"전화 {tel}")
    if fax: parts.append(f"팩스 {fax}")
    return " / ".join(parts)

def _get(info_map, key):  # 안전 get
    v = info_map.get(key)
    return v if isinstance(v, str) else None
# --- public API ---------------------------------------------
def load_index():
    return _load_all()

def search(query: str, top_k: int = 8, mmr_lambda: float = 0.6) -> List[Dict]:
    """
    기본 검색 함수:
      1) 질의 벡터화 → FAISS 검색(top_k*3개)
      2) 요약(summary) 항목에 가점
      3) MMR 재랭크 → 최종 top_k 결과 반환
    """
    index, texts, metas = _load_all()
    model = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")

    # 질의 벡터
    q = _norm(query)
    qvec = model.encode([q], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)

    # 1차: FAISS 검색 (여유있게 top_k*3 뽑음)
    scores, idx = index.search(qvec, top_k * 3)
    idx = idx[0]; scores = scores[0]

    # hits 구성
    hits = [{"i": int(i), "score": float(s), "text": texts[i], "meta": metas[i]}
            for i, s in zip(idx, scores) if i != -1]

    # 요약문(type=summary) 가점 (솔루션/비즈니스 요약을 우선 노출)
    for h in hits:
        m = h["meta"] or {}
        sec = (m.get("meta", {}) or {}).get("section") or m.get("section")
        typ = (m.get("meta", {}) or {}).get("type") or m.get("type")
        if (sec in ("solution", "business")) and (typ == "summary"):
            h["score"] += 0.2

    # MMR 재랭크
    doc_vecs = model.encode([_norm(h["text"]) for h in hits],
                            convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    order = _mmr(qvec[0], doc_vecs, k=min(top_k, len(hits)), lam=mmr_lambda)
    re_ranked = [hits[i] for i in order]
    return re_ranked[:top_k]

def rag_answer(query, top_k=5, **_):
    """
    고급 응답 함수:
    - 질의 intent를 분류하여 맞춤 응답:
      A) 회사 소개 → 슬로건 반환
      B) info 직답 (회사명, 대표이사 등)
      C) 연혁 질의 → 특정 연도/최신/전체
      D) 솔루션/비즈니스 → 요약 or 개별 항목
      E) 기본 → top1 스니펫
    """
    index, texts, metas = load_index()
    qnorm = _norm(query)

    # ---------- A) 회사 소개 의도 ----------
    if _is_company_intro_query(query):
        # 미리 지정된 대표 슬로건 3종
        want_titles = [
            "UltimateXperience, Trusted eXperitise",
            "Bumil Power to make Everything Possible",
            "Enjoy the Change!!",
        ]
        title_to_text = {}
        for i, m in enumerate(metas):
            meta = m.get("meta", {}) or {}
            sec = meta.get("section") or m.get("section")
            title = m.get("title") or meta.get("title") or m.get("id") or ""
            if sec == "main" and isinstance(texts[i], str):
                title_to_text[title] = texts[i].strip()

        lines = [title_to_text[t] for t in want_titles if t in title_to_text]

        # 부족하면 main 페이지의 짧은 슬로건 보충
        if len(lines) < 3:
            for i, m in enumerate(metas):
                meta = m.get("meta", {}) or {}
                if (meta.get("section") or m.get("section")) == "main":
                    txt = (texts[i] or "").strip()
                    if 0 < len(txt) <= 120 and "채용" not in txt and "보러가기" not in txt:
                        if txt not in lines:
                            lines.append(txt)
                if len(lines) >= 3:
                    break

        if lines:
            return "\n".join(lines)
    # 검색 실행
    hits = search(query, top_k=top_k)
    # ---------- B) info 직답 & 주소 질의 통일 처리 ----------
    info_map = _get_field_hits(metas, texts)

    # (B-0) 본사/지사 주소 의도 감지
    asks_addr = any(k in qnorm for k in ["주소", "위치", "어디"])
    asks_hq   = any(k in qnorm for k in ["본사", "대구본사", "본사 주소"])
    asks_branch_any = (any(k in qnorm for k in ["지사", "지점", "브랜치"])
                    or ("서울지사" in qnorm) or ("서울 지사" in qnorm))

    # --- 본사 ---
    if asks_addr and (asks_hq or not asks_branch_any) and ("본사주소" in info_map):
        addr = _strip_tail_from_addr(_get(info_map, "본사주소"))
        hq_contact = _get(info_map, "본사연락처") or _get(info_map, "연락처") or ""
        tel, fax = _extract_tel_fax(hq_contact)
        return _format_addr_line("본사", addr, tel, fax)

    # --- 특정 지사(서울지사) ---
    if asks_addr and (("서울지사" in qnorm) or ("서울 지사" in qnorm)):
        addr = _strip_tail_from_addr(_get(info_map, "지사주소_서울지사") or "")
        if addr:
            branch_contact = _get(info_map, "지사연락처_서울지사") or ""
            tel, fax = _extract_tel_fax(branch_contact)
            return _format_addr_line("서울지사", addr, tel, fax)

    # --- 지사 전체 목록 ---
    if asks_addr and asks_branch_any:
        lines = []
        for k, v in sorted(info_map.items()):
            if k.startswith("지사주소_"):
                branch = k.split("_", 1)[1]
                addr = v
                contact = _get(info_map, f"지사연락처_{branch}") or ""
                tel, fax = _extract_tel_fax(contact)
                lines.append(_format_addr_line(branch, addr, tel, fax))
        if lines:
            return "\n".join(lines)
    
    # (B-4) 일반 info 질의 매칭
    key_syn = {
        "회사명": ["회사명", "회사 이름", "사명", "사명은"],
        "설립연도": ["설립연도", "설립 년도", "언제 설립", "창립", "법인설립"],
        "대표이사": ["대표", "대표이사", "ceo"],
        "본사주소": ["본사", "주소", "본사 주소", "대구 주소"],
        "지사주소": ["지사", "지사 주소", "지점", "브랜치", "서울지사", "서울 지사", "branch", "office"],
        "연락처": ["연락처", "전화", "대표전화", "문의 메일", "이메일"],
        "비전": ["비전", "vision"],
        "미션": ["미션", "mission"],
    }

    # 기존 info 매칭 (본사주소/설립연도 등)
    matched_fields = []
    for field, kws in key_syn.items():
        if any(k.lower() in qnorm.lower() for k in kws):
            if field in info_map:
                matched_fields.append(field)
    if matched_fields:
        parts = [f"{f}: {info_map[f]}" for f in matched_fields]
        return " / ".join(parts)
    # ---------- C) 연혁 ----------
    def _join_lines(lines, year=None, sep="\n"):
        """연혁 라인에 연도 prefix 보정"""
        outs = []
        for t in lines:
            t_norm = _norm(t)
            if year and not re.search(r"\b(19|20)\d{2}\b", t_norm):
                outs.append(f"{year} - {t_norm}")
            else:
                m = re.search(r"\b((?:19|20)\d{2})\b", t_norm)
                if m and (not t_norm.startswith(m.group(1))):
                    outs.append(f"{m.group(1)} - {t_norm}")
                else:
                    outs.append(t_norm)
        return sep.join(outs)

    if ("연혁" in qnorm) or ("역사" in qnorm) or ("히스토리" in qnorm) or re.search(r"\b(19|20)\d{2}년", qnorm) or ("최신" in qnorm) or ("최근" in qnorm):
        hmap = _history_map(metas, texts)
        if not hmap:
            return "자료 부족"

        # 특정 연도
        y = re.search(r"\b((?:19|20)\d{2})년?", qnorm)
        if y:
            yy = y.group(1)
            if yy in hmap:
                return _join_lines(hmap[yy], year=yy)

        # 최신/최근
        if ("최신" in qnorm) or ("최근" in qnorm):
            max_year = max(hmap.keys())
            return _join_lines(hmap[max_year], year=max_year)

        # 전체 연혁 (연도 내림차순)
        items = sorted(hmap.items(), key=lambda kv: kv[0], reverse=True)
        out_lines = []
        for yy, lines in items:
            for ln in lines:
                out_lines.append(f"{yy} - {_norm(ln)}")
        return "\n".join(out_lines)

    # ---------- D) 솔루션/비즈니스 ----------
    sol_names = _collect_names(metas, "solution")
    biz_names = _collect_names(metas, "business")

    wants_solution = ("솔루션" in qnorm) or any(n.lower() in qnorm.lower() for n in sol_names)
    wants_business = ("비즈니스" in qnorm) or ("사업" in qnorm) or any(n.lower() in qnorm.lower() for n in biz_names)

    # 둘 다 요약
    if wants_solution and wants_business and any(k in qnorm for k in ["요약", "목록", "리스트", "전체", "종류"]):
        sol_txt = _get_by_id(metas, texts, "솔루션_요약")
        biz_txt = _get_by_id(metas, texts, "비즈니스_요약")
        parts = []
        if sol_txt: parts.append(f"[솔루션]\n{sol_txt}")
        if biz_txt: parts.append(f"[비즈니스]\n{biz_txt}")
        if parts:
            return "\n\n".join(parts)

    # 솔루션만
    if wants_solution:
        if any(k in qnorm for k in ["요약", "목록", "리스트", "전체", "종류"]):
            txt = _get_by_id(metas, texts, "솔루션_요약")
            if txt:
                return txt
        for name in sol_names:
            if name.lower() in qnorm.lower():
                txt = _get_by_id(metas, texts, f"솔루션_{name}")
                if txt:
                    return txt

    # 비즈니스만
    if wants_business:
        if any(k in qnorm for k in ["요약", "목록", "리스트", "전체", "종류"]):
            txt = _get_by_id(metas, texts, "비즈니스_요약")
            if txt:
                return txt
        for name in biz_names:
            if name.lower() in qnorm.lower():
                txt = _get_by_id(metas, texts, f"비즈니스_{name}")
                if txt:
                    return txt

    # ---------- E) 기본 ----------
    return hits[0]["text"] if hits else "자료 부족"