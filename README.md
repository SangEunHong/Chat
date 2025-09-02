# CustomChat Portal & RAG Chatbot

회사 포털용 **게시판(공지/질문/지식공유)** 과 회사 웹사이트 콘텐츠를 검색·요약해 주는 **RAG 챗봇**을 한 저장소에서 관리합니다.  
프론트는 React + Tailwind, 챗봇 파이프라인은 BeautifulSoup → 정제/청크 → Sentence-Transformer 임베딩 → **FAISS** → **MMR 재랭킹** → FastAPI 서빙 구조입니다.

> 데모 스크린샷/영상은 `docs/` 폴더에 넣고 아래 경로만 바꿔주세요.

---

## 📌 목차

- [기능](#-기능)
- [기술 스택](#-기술-스택)
- [아키텍처](#-아키텍처)
- [프로젝트 구조](#-프로젝트-구조)
- [빠른 시작](#-빠른-시작)
- [환경 변수 & 설정](#-환경-변수--설정)
- [주요 화면](#-주요-화면)
- [API 개요](#-api-개요)
- [운영/보안 참고](#-운영보안-참고)
- [로드맵](#-로드맵)
- [라이선스](#-라이선스)

---

## ✨ 기능

### 게시판 (Portal)
- 게시글 **목록/상세/작성/수정/삭제** (작성자 또는 관리자)
- 댓글 **작성/수정/삭제** (본인만)
- 회원 **가입/로그인(JWT)/마이페이지(정보·비번 수정)/탈퇴(본인확인)**
- **아이디 찾기(이름+휴대폰)**, **비밀번호 재설정(본인확인→토큰→새 비번)**
- 관리자 콘솔: **활성/탈퇴 분리**, 검색/페이징, **소프트 삭제/복구/하드 삭제/1년 경과 일괄 삭제**

### RAG 챗봇
- 회사 사이트(범일정보) **크롤링 → 텍스트 정제 → 청크/구조화 → 임베딩 → FAISS 검색**
- **요약 가점 + MMR 재랭킹(λ=0.6)** 로 중복 줄이고 다양성 확보
- **회사 소개/슬로건**, **본사/지사 주소·연락처**, **연혁(특정/최신/전체)**,  
  **비전·미션**, **솔루션/비즈니스 요약·상세** 등 의도별 정규화 응답
- 프론트 연동: 입력 IME(한글) 안전 처리, **경과시간/ETA** 표시 UX

---

## 🛠 기술 스택

**Frontend**
- React, React Router, Tailwind CSS, react-icons
- fetch API, LocalStorage (JWT 캐싱/멀티탭 동기화)

**Backend(API)**
- (게시판) FastAPI (예시), JWT 인증, REST
- (챗봇) FastAPI (`/rag/ask`), Sentence-Transformers, **FAISS (IndexFlatIP)**

**Data/RAG**
- requests, BeautifulSoup4
- sentence-transformers: **BAAI/bge-m3**
- faiss-cpu, numpy, regex, tqdm

---

## 🧱 아키텍처

```
[React Frontend]
  ├─ /login /signup /mypage /posts /admin ...
  └─ /chat  ────────────────▶  [RAG API :9001]
                                 │  /rag/ask (질의)
                                 ▼
                   [RAG Pipeline (Python/FastAPI)]
  crawl → clean → chunk → embed(BAAI/bge-m3, normalize) → FAISS(IP) → MMR re-rank
                                 │
                                 └─ 의도 라우팅(회사정보/연혁/주소/요약/기본 스니펫)
```

---

## 📁 프로젝트 구조

### 📂 CHAT (게시판 & 사용자 관리 웹앱)
```
CHAT/
├── backend/
│ ├── pycache/
│ ├── routers/
│ │ ├── pycache/
│ │ ├── init.py
│ │ ├── admin_users.py
│ │ ├── chat.py
│ │ ├── comments.py
│ │ ├── post.py
│ │ └── user.py
│ ├── venv/
│ ├── auth.py
│ ├── crud.py
│ ├── database.py
│ ├── main.py
│ ├── models.py
│ └── schemas.py
│
├── frontend/
│ ├── node_modules/
│ ├── public/
│ └── src/
│ ├── components/
│ │ ├── chat/
│ │ ├── Footer.jsx
│ │ └── Sidebar.jsx
│ ├── pages/
│ │ ├── admin/
│ │ │ └── AdminUsersPage.jsx
│ │ ├── ChatPage.jsx
│ │ ├── LoginPage.jsx
│ │ ├── MainPage.jsx
│ │ ├── MyPage.jsx
│ │ ├── PostDetailPage.jsx
│ │ ├── PostEditPage.jsx
│ │ ├── SignupPage.jsx
│ │ └── WritePage.jsx
│ ├── App.js
│ ├── index.css
│ ├── index.js
│ └── Layout.jsx
│
├── reportWebVitals.js
├── setupTests.js
├── .gitignore
├── package-lock.json
├── package.json
├── postcss.config.js
├── README.md
├── tailwind.config.js
└── .env
```
### 📂 CHATT (회사 정보 RAG 챗봇 서버)
```
CHATT/
├─ .venv/ # 가상환경
├─ crawler/ # 원문 수집
│ ├─ init.py
│ └─ web_crawler.py
├─ data/ # 전처리 단계 산출물
│ ├─ raw.jsonl # 크롤링 원문
│ ├─ clean.jsonl # 클린 텍스트
│ └─ chunks.jsonl # 청크 결과
├─ processor/ # 전처리 파이프라인
│ ├─ init.py
│ ├─ cleaner.py # 노이즈 제거/정규화
│ └─ chunker.py # 문서 청크 분할
├─ embedder/ # 임베딩 생성
│ ├─ init.py
│ └─ embed_faiss.py # FAISS용 벡터 생성/저장
├─ index/ # 검색 인덱스 및 메타
│ ├─ faiss_ip.index # FAISS InnerProduct 인덱스
│ ├─ metas.jsonl # 청크 메타데이터
│ └─ texts.jsonl # 청크 원문 저장
├─ rag/ # RAG 검색/조회
│ ├─ init.py
│ └─ search.py # 쿼리→검색→리트리브 로직
├─ utils/ # 공용 유틸
│ ├─ init.py
│ ├─ file_utils.py # 파일 I/O
│ └─ text_utils.py # 텍스트 헬퍼
├─ config.py # 경로/모델/파라미터 설정
├─ main.py # 파이프라인 엔트리/배치 스크립트
├─ service.py # API 서버 엔트리
└─ requirements.txt # 의존성 목록
```
---

## ⚡ 빠른 시작

### 0) 사전 준비
- Node.js 18+
- Python 3.10+ (가급적 3.10~3.11)
- (게시판 API 서버는 8000 포트로 기동되어 있다고 가정)

### 1) 프론트엔드
```bash
# 루트(또는 client/)에서
npm install
npm start            # http://localhost:3000
```

### 2) RAG 파이프라인 & API
```bash
# 가상환경 권장
python -m venv .venv
.\.venv\Scripts\Activate

# 필수 패키지
pip install -U pip
pip install -r requirements.txt
# 없으면 아래로 설치
# pip install fastapi uvicorn[standard] requests beautifulsoup4 tqdm numpy faiss-cpu sentence-transformers pydantic

# 데이터 구축 (크롤링 → 정제 → 청크 → 임베딩/FAISS)
python main.py

# RAG 서버 실행
uvicorn service:app --host 0.0.0.0 --port 9001
```

동작 확인:
```bash
curl -X POST http://localhost:9001/rag/ask   -H "Content-Type: application/json"   -d '{"question":"본사 주소 알려줘"}'
```

---

## 🔧 환경 변수 & 설정

- `config.py`
  - `BASE_URL` : 크롤링 베이스(범일정보)
  - `DATA_DIR/INDEX_DIR` : 데이터/인덱스 저장 폴더
  - `EMBED_MODEL_NAME` : `BAAI/bge-m3` (기본)
  - `GEN_*` : (옵션) 생성모델 설정 값 자리 (현재 RAG 중심)
- 포트
  - 게시판 API: `:8000` (별도 서버)
  - RAG API: `:9001` (이 저장소의 `service.py`)

> 프런트는 `.env`를 쓰지 않고 있어 URL 변경은 파일 내 상수 변경 또는 프록시 권장.

---

## 🖼 주요 화면

- [ ] 대시보드/목록 (`docs/screen-dashboard.png`)
- [ ] 게시글 상세+댓글 (`docs/screen-post.png`)
- [ ] 글 작성/수정 (`docs/screen-write.png`)
- [ ] 로그인/회원가입 (`docs/screen-auth.png`)
- [ ] 마이페이지 (`docs/screen-mypage.png`)
- [ ] 관리자-회원관리 (`docs/screen-admin.png`)
- [ ] 챗봇 UI (`docs/screen-chat.png`)

> 이미지를 `docs/` 폴더에 두고 README의 경로만 맞춰주세요.

---

## 🧩 API 개요

### 게시판(예시, :8000)
- Auth/Account  
  `POST /login`, `POST /signup`, `GET /verify-token`  
  `GET /mypage`, `PUT /mypage/update`, `DELETE /mypage/delete`
- Password/ID  
  `POST /password/reset-start`, `POST /password/reset-confirm`, `POST /find-id`
- Posts  
  `GET/POST /posts`, `GET/PUT/DELETE /posts/{id}`
- Comments  
  `GET/POST /posts/{id}/comments`, `PUT/DELETE /comments/{id}`
- Admin  
  `GET /admin/users?status=active|deleted&q=&page=&size=`  
  `PATCH /admin/users/{userID}/soft-delete`  
  `PATCH /admin/users/{userID}/restore`  
  `DELETE /admin/users/{userID}`  
  `POST /admin/users/purge-expired`

### RAG(:9001)
- `POST /rag/ask`
  - Request: `{"question": "연혁 최신 알려줘", "top_k": 8}`
  - Response: `{"answer": "..."}`

---

## 🛡 운영/보안 참고

- 프론트는 JWT를 LocalStorage에 저장 → 운영 전환 시 **httpOnly 쿠키** 고려
- 관리자 API는 서버단에서 **role 검사 필수**
- 탈퇴 사용자는 `is_deleted + deleted_at`으로 유지 후 **주기 purge** (1년 경과)
- RAG 인덱스는 파이프라인 재실행으로 갱신(배치/크론)

---

## 🗺 로드맵

- [ ] RAG 응답에 **출처(청크 근거)** 링크/하이라이트 추가  
- [ ] 대규모 대응: IVF/HNSW 인덱스 전환 + 파라미터 튜닝  
- [ ] 사내 문서(PDF/Word) 파서 및 권한 연동형 RAG  
- [ ] SFT(LoRA) 파이프라인 정비(`sft/`) 및 평가 리포트  
- [ ] 프론트 API URL 환경변수(.env)화

---

## 📄 라이선스

- 제안: **MIT License** (원하면 `LICENSE` 파일 추가)

---

### 부록) `requirements.txt` 예시

```txt
fastapi
uvicorn[standard]
requests
beautifulsoup4
tqdm
numpy
faiss-cpu
sentence-transformers
pydantic>=2
```
