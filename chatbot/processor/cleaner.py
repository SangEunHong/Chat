# processor/cleaner.py
"""
RAW 크롤링 결과(raw.jsonl)를 읽어서
- content 필드의 텍스트를 정제(clean_text 적용)
- 너무 짧은(의미 없는) 레코드는 제거
- 정제된 JSON Lines 파일(clean.jsonl)로 저장

즉, 크롤링된 잡음을 간단히 필터링하고, 학습/RAG 인덱싱에 쓸 수 있는
깔끔한 텍스트 코퍼스를 만든다.
"""
import json, re
from pathlib import Path
from config import RAW_PATH, CLEAN_PATH, DATA_DIR
from utils.text_utils import clean_text
from utils.file_utils import ensure_dir

def build_clean():
    """
    raw.jsonl → clean.jsonl 변환 파이프라인
    Steps:
    1. RAW_PATH 열기
    2. 각 라인(JSON dict) 파싱
    3. content 필드 정제(clean_text 호출)
       - 공백/특수문자/줄바꿈 정리 등
    4. 길이가 너무 짧은 콘텐츠(<20자)는 버림
    5. 남은 레코드를 clean.jsonl에 기록
    6. 몇 개 저장했는지 출력
    """
    ensure_dir(DATA_DIR)  # data 디렉토리 없으면 생성
    count = 0

    with open(RAW_PATH, encoding="utf-8") as f, \
         open(CLEAN_PATH, "w", encoding="utf-8") as w:
        for line in f:
            rec = json.loads(line)                # JSON 한 줄 로드
            content = clean_text(rec.get("content", ""))  # 텍스트 정제
            if len(content) < 20:                 # 너무 짧으면 skip
                continue
            rec["content"] = content              # 정제된 content로 덮어쓰기
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")  # 출력 파일에 append
            count += 1

    print(f"✔️ [정제] clean.jsonl 저장 ({CLEAN_PATH}) - {count}개")