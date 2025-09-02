# utils/text_utils.py
import re

def clean_text(text: str) -> str:
    """
    크롤링한 원문에서 불필요한 공백/특수문자 등을 제거하고
    RAG 인덱싱에 적합한 '깔끔한' 문장으로 정리한다.

    주요 처리:
    1. HTML 엔티티/태그 제거 (필요시 BeautifulSoup에서 1차 처리)
    2. \r, \n, \t 같은 제어문자 제거
    3. 연속 공백/줄바꿈 → 단일 공백으로 변환
    4. 앞뒤 공백 trim
    5. 의미 없는 placeholder 제거 (예: &nbsp;, "더보기", "닫기" 등)
    """
    if not text:
        return ""

    # 1) HTML 엔티티 일부 정리
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    # 2) 제어문자(\r, \n, \t) → 공백
    text = re.sub(r"[\r\n\t]+", " ", text)
    # 3) 다중 공백 → 하나의 공백
    text = re.sub(r"\s+", " ", text)
    # 4) 광고/불필요 키워드 같은 패턴 제거 (예시)
    #    "더보기", "닫기", "관련기사" 같은 UI 잔여물
    text = re.sub(r"(더보기|닫기|관련기사)", "", text)
    # 5) 앞뒤 공백 제거
    text = text.strip()
    return text