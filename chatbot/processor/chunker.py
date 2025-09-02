# chunker.py
# -----------------------------------------------------------------------------
# 역할: clean.jsonl(정제본)을 읽어 아래 2종류의 청크를 생성하여 chunks.jsonl로 저장
#   1) 원본 문장 기반 청크: 길이(target_chars) 기준으로 문장 단위 슬라이딩 윈도우 청크
#   2) 구조화 청크: info(회사명/설립연도/대표이사/주소/연락처/비전/미션), history(연도별),
#                  solution/business(항목별 상세), summary(목록 요약)
#
# 특징:
#   - 내비/푸터/메뉴 같은 노이즈 블록을 필터링
#   - HISTORY는 "2010-현재" 같은 범위 헤더를 건너뛰고, "YYYY" 단일 헤더,
#     "YYYY 내용" 한 줄 표기 등 다양한 케이스를 연도별로 안전하게 수집
#   - 연락처(전화/팩스/문의메일) 등은 필드별로 탐지 후 하나의 info 레코드로 합침
#   - 솔루션/비즈니스는 항목별 본문에서 홍보성/페이지 이동 텍스트를 제거
#   - 요약(summary)은 UI/QA에서 빠르게 목록을 노출할 때 사용
# -----------------------------------------------------------------------------
import json, re
from config import CLEAN_PATH, CHUNKS_PATH, DATA_DIR
from utils.text_utils import clean_text
from utils.file_utils import ensure_dir

_PHONE_RE = re.compile(r"(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})")
_TEL_RE   = re.compile(r"(?:T\.|Tel|전화)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", re.I)
_FAX_RE   = re.compile(r"(?:F\.|팩스)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", re.I)

# 문장 단위 분리
def split_sentences(text: str):
    """
    텍스트를 문장 단위로 크게 분할
    - 마침표/물음표/느낌표 뒤 공백을 경계로 분리
    - 줄바꿈(\n, \r)도 문장 경계로 취급
    - 특수 케이스(약어 'e.g.', 'i.e.' 등)는 완벽히 처리하지 않지만,
      이후 슬라이딩 윈도우로 재결합(overlap)하여 의미 단절 완화
    """
    return re.split(r"(?<=[.!?])\s+|[\n\r]+", text)

def _clip_addr(line: str) -> str:
    """
    주소 뒤에 흔히 붙는 꼬리(T./T :/Tel/전화/F./F :/팩스/지도바로가기/아이콘/본사/지사/서울지사/라벨 없는 전화번호)를 만나면 그 이전까지만 남긴다.
    """
    m = re.search(
        r"""^(.*?)
            (?=\s*(?:                # 다음 꼬리 직전까지 캡쳐
                 T\s*[.:]            # T. / T: / T : 
                |Tel
                |전화
                |F\s*[.:]            # F. / F: / F :
                |팩스
                |지도\s*바로가기
                |바로가기
                |아이콘
                |본사
                |지사
                |서울\s*지사
                |0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}   # 라벨 없는 전화번호
            )|$)""",
        line,
        flags=re.I | re.X,
    )
    base = m.group(1).strip() if m else (line or "").strip()
    # 혹시 남은 꼬리 어휘 제거
    base = re.sub(r"\s*(?:본사|지사|서울\s*지사)\s*$", "", base, flags=re.I)
    base = re.sub(r"\s{2,}", " ", base)
    return base

def _find_earliest_year(text: str):
    """
    텍스트에서 1900~2099 사이 연도를 모두 찾고 가장 이른 연도를 반환합니다.
    HISTORY 섹션에서 '설립연도' 보정에 활용합니다.
    """
    yrs = re.findall(r"((?:19|20)\d{2})", text)
    return min(yrs) if yrs else None

# HISTORY 파서 (연도별 블록화)
def _is_year_header(line: str) -> bool:
    """'2021' 같은 단일 연도 헤더인지 검사"""
    return bool(re.match(r"^\s*(?:19|20)\d{2}\s*$", line))

def _is_range_header(line: str) -> bool:
    """'2010-현재' 또는 '2000-2009' 같은 범위 헤더인지 검사"""
    return bool(re.match(r"^\s*(?:19|20)\d{2}\s*-\s*(?:현재|(?:19|20)\d{2})\s*$", line))

def _parse_history_blocks(text: str):
    """
    HISTORY 본문을 연도별로 묶어 [(year, '한 줄 텍스트'), ...] 반환합니다.

    처리 규칙
    - '2010-현재' 같은 범위 헤더는 건너뜁니다(연도 미정이라 이벤트로 사용 불가).
    - 'YYYY' 단일 연도 헤더를 만나면 이후 연도 표기가 없는 라인들은 그 연도로 귀속됩니다.
    - 'YYYY 내용'처럼 한 줄에 연도+내용이 함께 있으면 그대로 저장합니다.
    - 연도 추출 불가 라인은 버립니다(노이즈/설명 부제 등).
    """
    lines = [clean_text(ln) for ln in (text or "").splitlines()]
    out = []
    cur_year = None

    for ln in lines:
        if not ln:
            continue

        # 범위 헤더 스킵(연도 미확정 블록)
        if _is_range_header(ln):
            cur_year = None
            continue

        # 단일 연도 헤더
        if _is_year_header(ln):
            cur_year = re.search(r"((?:19|20)\d{2})", ln).group(1)
            continue

        # 본문 라인 안에 연도 포함 → 그 연도로 즉시 기록
        m = re.search(r"\b((?:19|20)\d{2})\b", ln)
        if m:
            year = m.group(1)
            out.append((year, ln))
            continue

        # 연도 표기는 없지만 직전 연도 헤더가 있다 → 그 연도로 귀속
        if cur_year:
            out.append((cur_year, ln))
            continue

        # 그 외는 무시(연도 추출 불가)
    return out
def _extract_tel_fax(s: str):
    tel = None; fax = None
    mt = _TEL_RE.search(s or "");  mf = _FAX_RE.search(s or "")
    if mt: tel = mt.group(1)
    if mf: fax = mf.group(1)
    if not tel:  # 라벨 없이 숫자만 있는 경우
        m = _PHONE_RE.search(s or "")
        if m: tel = m.group(1)
    return tel, fax

# 정보 추출 (clean.jsonl → 사전)
def extract_info_chunks(clean_path):
    """
    clean.jsonl을 훑으며 구조화 가능한 정보들을 모읍니다.
    반환: info 딕셔너리 (아래 build_chunks()에서 실제 청크 레코드로 변환)
    """
    info = {
        "회사명": None,
        "설립연도": None,     # '1991년' 형태로 저장
        "대표이사": None,
        "본사주소": None,
        "지사주소": {},       # 예: {"서울지사": "서울 …"}
        "연락처": None,        # "제품문의 xxx, 기술문의 yyy, 대표전화 02-..." 한 줄
        "본사연락처": {"tel": None, "fax": None},   
        "지사연락처": {},                            
        "미션": None,
        "연혁": [],           # (year, text) 튜플 리스트
        "솔루션": [],          # [(name, body)]
        "비즈니스": []         # [(name, body)]
    }

    # 연락처를 각 필드로 먼저 수집 → 마지막에 한 줄로 합쳐 info["연락처"]로 저장
    contact_fields = {
        "대표전화": None,
        "팩스": None,
        "제품문의": None,
        "기술문의": None,
        "개발문의": None
    }

    with open(clean_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            title = rec.get("title", "") or ""
            txt = rec.get("content", "") or ""
            section = rec.get("section", "") or ""

            # 회사명: 등장 여부로 간단하게 감지(사이트 특화)
            if info["회사명"] is None and ("범일정보" in title or "범일정보" in txt):
                info["회사명"] = "범일정보"

            # (A) 설립연도 '강한 시그널' 패턴: "1991.07 회사 설립", "법인 설립 1991" 등
            if info["설립연도"] is None:
                strong_pats = [
                    r"\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b[^\n]{0,20}?(?:회사|법인|범일정보)[^\n]{0,10}?설립",
                    r"(?:회사|법인|범일정보)[^\n]{0,10}?설립[^\n]{0,20}?\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b",
                    r"\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b[^\n]{0,20}?(?:창립|법인\s*설립)",
                    r"(?:창립|법인\s*설립)[^\n]{0,20}?\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b",
                ]
                for pat in strong_pats:
                    m = re.search(pat, txt)
                    if m:
                        info["설립연도"] = f"{m.group(1)}년"
                        break

            # (B) HISTORY 블록: 연혁 리스트 확장 + 최솟값으로 설립연도 보정
            if ("연혁" in title) or ("HISTORY" in title.upper()):
                parsed = _parse_history_blocks(txt)  # [(year, text)]
                info["연혁"].extend(parsed)

                earliest = _find_earliest_year(txt)
                if earliest:
                    cur = (info["설립연도"] or "").rstrip("년") or "9999"
                    if earliest < cur:
                        info["설립연도"] = f"{earliest}년"

            # (C) '약한 시그널' 패턴: "1991 설립", "설립 1991" 같이 단서가 짧은 경우
            if info["설립연도"] is None:
                weak_pats = [
                    r"\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b[^\n]{0,10}?설립",
                    r"설립[^\n]{0,10}?\b((?:19|20)\d{2})(?:[.\-/]\d{1,2})?\b",
                ]
                for pat in weak_pats:
                    m = re.search(pat, txt)
                    if m:
                        info["설립연도"] = f"{m.group(1)}년"
                        break

            # 대표이사(사이트 특화 키워드)
            if info["대표이사"] is None and "박영기" in txt:
                info["대표이사"] = "박영기"
            # --- 본사 주소 + 연락처 동시 추출 (통일본) ---
            if info["본사주소"] is None and "대구광역시" in txt:
                # 쉼표 제한([^\n,]+) 제거 → 라인 끝까지 먼저 잡고 _clip_addr로 꼬리 컷
                m = re.search(r"(대구광역시[^\n]+)", txt)
                if m:
                    raw = m.group(1)
                    info["본사주소"] = _clip_addr(raw)  # 주소만
                    # 같은 블록에서 tel/fax도 최대한 추출
                    tel, fax = _extract_tel_fax(txt)
                    if tel: info["본사연락처"]["tel"] = tel
                    if fax: info["본사연락처"]["fax"] = fax

            # --- 서울지사 주소 + 연락처 동시 추출 ---
            if "서울지사" in txt or "서울 지사" in txt or "서울지사" in title:
                m = re.search(r"(서울[^\n]+)", txt)
                if m:
                    raw = m.group(1)
                    addr_only = _clip_addr(raw)  # ← 여기서 강력 컷오프
                    info["지사주소"]["서울지사"] = addr_only
                    # tel/fax도 같은 블록에서 추출 (지사연락처 저장)
                    tel, fax = _extract_tel_fax(txt)
                    info["지사연락처"].setdefault("서울지사", {"tel": None, "fax": None})
                    if tel: info["지사연락처"]["서울지사"]["tel"] = tel
                    if fax: info["지사연락처"]["서울지사"]["fax"] = fax
            # 연락처(전화/팩스)
            if contact_fields["대표전화"] is None:
                m = re.search(r"(?:대표전화|전화|Tel|T\.)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", txt)
                if m: contact_fields["대표전화"] = m.group(1)
            if contact_fields["팩스"] is None:
                m = re.search(r"(?:팩스|F\.)[:：]?\s*(0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", txt)
                if m: contact_fields["팩스"] = m.group(1)

            # 문의 메일(제품/기술/개발)
            if contact_fields["제품문의"] is None:
                m = re.search(r"제품문의[:：]?\s*([^\s,]+@[^\s,]+)", txt)
                if m: contact_fields["제품문의"] = m.group(1)
            if contact_fields["기술문의"] is None:
                m = re.search(r"기술문의[:：]?\s*([^\s,]+@[^\s,]+)", txt)
                if m: contact_fields["기술문의"] = m.group(1)
            if contact_fields["개발문의"] is None:
                m = re.search(r"개발문의[:：]?\s*([^\s,]+@[^\s,]+)", txt)
                if m: contact_fields["개발문의"] = m.group(1)

            # 비전/미션: 제목 신호가 가장 정확함(본문 키워드는 중복/잡음 가능)
            if not info["비전"] and ("비전" in title or "VISION" in title.upper()):
                info["비전"] = txt.strip()
            if not info["미션"] and ("미션" in title or "MISSION" in title.upper()):
                info["미션"] = txt.strip()

            # 솔루션/비즈니스 항목 수집
            if section == "solution" and title and txt:
                info["솔루션"].append((title.strip(), txt.strip()))
            if section == "business" and title and txt:
                info["비즈니스"].append((title.strip(), txt.strip()))

    # 연락처 통합 문자열 생성(필드가 있는 것만 순서대로 연결)
    contact_answer = []
    if contact_fields["제품문의"]: contact_answer.append("제품문의 " + contact_fields['제품문의'])
    if contact_fields["기술문의"]: contact_answer.append("기술문의 " + contact_fields['기술문의'])
    if contact_fields["개발문의"]: contact_answer.append("개발문의 " + contact_fields['개발문의'])
    if contact_fields["대표전화"]: contact_answer.append("대표전화 " + contact_fields['대표전화'])
    if contact_fields["팩스"]: contact_answer.append("팩스 " + contact_fields['팩스'])
    info["연락처"] = ", ".join(contact_answer) if contact_answer else None

    return info

# 네비/푸터 노이즈 필터
def _is_nav_noise(title: str, content: str) -> bool:
    """
    네비게이션/푸터/메뉴/저작권/채용/외부 링크 등 검색에 방해되는 블록을 식별.
    - 'COMPANY/BUSINESS/...' 등 상단 메뉴 텍스트
    - SNS/인트라넷/저작권 문구
    """
    t = (title or "")
    c = (content or "")
    if "퀵 메뉴" in t or "주메뉴" in t:
        return True
    if re.search(r"\b(COMPANY|BUSINESS|SOLUTION|RECRUIT|LOCATION)\b", c, re.I):
        return True
    if "facebook" in c.lower() or "intranet" in c.lower():
        return True
    if "개인정보처리방침" in c or "All Rights Reserved" in c:
        return True
    return False

# 청크 빌드 (메인 엔트리)
def build_chunks(target_chars=800, overlap=100):
    """
    clean.jsonl → chunks.jsonl
    1) 원본 문장 기반 청크
       - 문장 경계 분할 후 target_chars를 넘지 않도록 슬라이딩 윈도우 결합
       - 청크 간 overlap을 주어 문맥 단절을 완화
    2) 구조화 청크
       - info/history/solution/business/summary 레코드 추가
    """
    ensure_dir(DATA_DIR)

    # 1) 원본 청크 (문장 단위, 노이즈 제외)
    with open(CLEAN_PATH, encoding="utf-8") as f, open(CHUNKS_PATH, "w", encoding="utf-8") as w:
        idx = 0
        for line in f:
            rec = json.loads(line)
            title = rec.get("title", "")
            content = rec.get("content", "")

            # 네비/푸터 등 노이즈는 통째로 건너뜀
            if _is_nav_noise(title, content):
                continue

            sents = split_sentences(content)
            buf = ""
            for sent in sents:
                # 현재 버퍼 + 다음 문장이 target_chars를 넘으면 플러시
                if len(buf) + len(sent) > target_chars and buf:
                    w.write(json.dumps({
                        "id": f"{title or 'NA'}_{idx}",
                        "text": buf.strip(),
                        "meta": rec
                    }, ensure_ascii=False) + "\n")
                    # overlap 만큼 꼬리를 남겨 다음 청크와 문맥 연결
                    buf = buf[-overlap:]
                    idx += 1
                buf += sent + " "

            # 마지막 버퍼 잔여분도 출력
            if buf.strip():
                w.write(json.dumps({
                    "id": f"{title or 'NA'}_{idx}",
                    "text": buf.strip(),
                    "meta": rec
                }, ensure_ascii=False) + "\n")

    # 2) info / history / solution / business / summary
    #    (※ 반드시 원본 청크 쓰기 이후, 루프 바깥에서 한 번만 호출)
    info = extract_info_chunks(CLEAN_PATH)

    def _strip_noise(text: str) -> str:
        """
        솔루션/비즈니스 본문에 섞이는 자주 보이는 잡텍스트 정리
        - '더 알아보기', '페이지1' 같은 안내성/페이지 네비게이션 텍스트 제거
        - 다중 공백 축소
        """
        t = (text or "")
        t = re.sub(r"\s*더 알아보기\s*", " ", t)
        t = re.sub(r"\s+페이지\d+\s*", " ", t)
        t = re.sub(r"\s{2,}", " ", t).strip()
        return t

    #  이 블록 안에서만 w.write() 호출 (파일 닫히기 전까지 한 번에 작성)
    with open(CHUNKS_PATH, "a", encoding="utf-8") as w:
        # 2-1) 단일 필드 → info 섹션 레코드로 저장
        for k in ["회사명", "설립연도", "대표이사", "본사주소", "연락처", "비전", "미션"]:
            v = info.get(k)
            if v:
                w.write(json.dumps({
                    "id": k,
                    "text": v,
                    "meta": {"section": "info"}
                }, ensure_ascii=False) + "\n")

        # 2-1-추가) 지사주소 각각 저장 (예: id="지사주소_서울지사")
        for branch_name, addr in (info.get("지사주소") or {}).items():
            if addr:
                w.write(json.dumps({
                    "id": f"지사주소_{branch_name}",
                    "text": addr,
                    "meta": {"section": "info", "branch": branch_name}
                }, ensure_ascii=False) + "\n")

        # 2-1-추가) 본사연락처 저장 (전화/팩스만)
        hq_tel = (info.get("본사연락처") or {}).get("tel")
        hq_fax = (info.get("본사연락처") or {}).get("fax")
        if hq_tel or hq_fax:
            line = " / ".join([p for p in [
                f"전화 {hq_tel}" if hq_tel else None,
                f"팩스 {hq_fax}" if hq_fax else None
            ] if p])
            w.write(json.dumps({
                "id": "본사연락처",
                "text": line,
                "meta": {"section": "info"}
            }, ensure_ascii=False) + "\n")

        # 2-1-추가) 지사연락처_* 저장
        for branch_name, cf in (info.get("지사연락처") or {}).items():
            tel = (cf or {}).get("tel")
            fax = (cf or {}).get("fax")
            if tel or fax:
                line = " / ".join([p for p in [
                    f"전화 {tel}" if tel else None,
                    f"팩스 {fax}" if fax else None
                ] if p])
                w.write(json.dumps({
                    "id": f"지사연락처_{branch_name}",
                    "text": line,
                    "meta": {"section": "info", "branch": branch_name}
                }, ensure_ascii=False) + "\n")

        # 2-2) 연혁 저장
        seen_hist = set()
        for year, line in info.get("연혁", []):
            t = _strip_noise(line)
            if not t:
                continue
            key = (year, t)
            if key in seen_hist:
                continue
            seen_hist.add(key)
            w.write(json.dumps({
                "id": f"연혁_{year}",
                "text": t,
                "meta": {"section": "history", "year": year}
            }, ensure_ascii=False) + "\n")

        # 2-3) 솔루션/비즈니스 항목 저장
        sol_names = []
        for title, txt in info.get("솔루션", []):
            name = (title or "").strip()
            body = _strip_noise(txt or "")
            if name and body:
                sol_names.append(name)
                w.write(json.dumps({
                    "id": f"솔루션_{name}",
                    "text": body,
                    "meta": {"section": "solution", "name": name}
                }, ensure_ascii=False) + "\n")

        biz_names = []
        for title, txt in info.get("비즈니스", []):
            name = (title or "").strip()
            body = _strip_noise(txt or "")
            if name and body:
                biz_names.append(name)
                w.write(json.dumps({
                    "id": f"비즈니스_{name}",
                    "text": body,
                    "meta": {"section": "business", "name": name}
                }, ensure_ascii=False) + "\n")

        # 2-4) 요약 저장
        if sol_names:
            w.write(json.dumps({
                "id": "솔루션_요약",
                "text": ", ".join(sol_names),
                "meta": {"section": "solution", "type": "summary"}
            }, ensure_ascii=False) + "\n")

        if biz_names:
            w.write(json.dumps({
                "id": "비즈니스_요약",
                "text": ", ".join(biz_names),
                "meta": {"section": "business", "type": "summary"}
            }, ensure_ascii=False) + "\n")

    print("✔️ [청크] chunks.jsonl 저장 (원본+info/연혁(연도별)/솔루션/비즈니스/요약)")