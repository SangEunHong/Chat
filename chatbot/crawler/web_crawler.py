"""
범일정보 홈페이지용 간단 크롤러.

구성:
- fetch_soup(url): 요청 + 인코딩 보정 + BeautifulSoup 객체 반환
- crawl_main_page(): 메인 페이지의 섹션(H1~H4)별 제목/본문 크롤링
- crawl_solution_page(): 솔루션 목록(이름/설명/주요기능/특징/메타정보) 크롤링
- crawl_business_pages(): 비즈니스(클라우드, 인프라, 플랫폼 등) 요약 설명 크롤링
- crawl_all(): 전체 파이프라인 실행

출력:
- 결과는 JSON Lines 형식으로 RAW_PATH에 append/write 저장.
  각 라인은 {"url","section","title","content"} 구조를 가짐.
"""
import requests, json, re, time
from bs4 import BeautifulSoup
from pathlib import Path
from config import BASE_URL, RAW_PATH, DATA_DIR
from utils.text_utils import clean_text
from utils.file_utils import ensure_dir

# 요청에 사용할 UA 헤더 (간단한 봇 차단 회피/서버 친화)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

def fetch_soup(url: str) -> BeautifulSoup:
    """
    단일 URL에 대해 HTTP GET 요청을 수행하고 BeautifulSoup으로 파싱해 반환.

    - resp.apparent_encoding을 통해 서버가 명시하지 않은 인코딩을 추정하여
      깨짐 방지 (특히 한글 사이트 대응)
    - 반환: 파싱된 BeautifulSoup 객체
    """
    resp = requests.get(url, headers=HEADERS, timeout=10)
    # 일부 서버가 잘못된/누락된 인코딩 헤더를 보내는 경우가 있어 보정
    resp.encoding = resp.apparent_encoding
    html = resp.text
    return BeautifulSoup(html, "html.parser")

def crawl_main_page():
    """
    메인 페이지(BASE_URL)의 H1~H4 섹션을 순회하며:
    - 제목: 해당 헤딩 태그 텍스트
    - 본문: 다음 형제(sibling) 블록들을 H 태그를 만나기 전까지 이어붙여 수집
    수집된 (제목, 본문)을 JSONL로 RAW_PATH에 저장.

    메인 페이지 섹션 카드/블록 기반의 단순 구조에 맞춘 제너럴한 수집 로직.
    """
    ensure_dir(DATA_DIR)
    url = BASE_URL
    soup = fetch_soup(url)

    # h1~h4 제목 블록을 섹션 단위로 간주
    h_tags = soup.find_all(re.compile("^h[1-4]$"))
    items = []

    for h in h_tags:
        title = clean_text(h.get_text())

        # 같은 섹션으로 볼 수 있는 '다음 형제'들을 H 태그가 나오기 전까지 이어붙임
        content = []
        sib = h.find_next_sibling()
        while sib and not re.match(r"h[1-4]", sib.name or ""):
            if hasattr(sib, "get_text"):
                t = clean_text(sib.get_text())
                if t:
                    content.append(t)
            sib = sib.find_next_sibling()

        # 최소 (제목+본문) 쌍이 있는 경우만 결과에 넣음
        if title and content:
            items.append({
                "url": url,
                "section": "main",   # 섹션 종류
                "title": title,      # 섹션 제목(H1~H4)
                "content": " ".join(content)  # 섹션 본문(문단 합침)
            })

    # 결과 저장 (메인은 새로 덮어씀)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✔️ [크롤러] main page: {len(items)}개 저장 ({RAW_PATH})")

def crawl_solution_page():
    """
    솔루션 페이지(/page/solution.html)에서 솔루션 카드(.sSol_box)를 모두 수집:
    - title: 솔루션 이름(strong) + 보조 설명(h4)
    - content: 설명, 주요기능(ul>li), 특징(.sSol_char), 부가메타(.sSol_ex) 등을 통합

    주의:
    - CSS 클래스/DOM 구조 변화에 취약하므로, 사이트 개편 시 선택자 점검 필요.
    """
    url = BASE_URL + "page/solution.html"
    soup = fetch_soup(url)

    sol_boxes = soup.find_all("div", class_="sSol_box")
    items = []

    for box in sol_boxes:
        # 솔루션명 (예: Chainform 등) — 사이트 구조에 맞춘 선택자
        sol_name_tag = box.find("strong")
        sol_name = sol_name_tag.get_text(strip=True) if sol_name_tag else ""

        # 간단 설명 (보조 제목)
        desc_tag = box.find("h4")
        desc = desc_tag.get_text(strip=True) if desc_tag else ""

        # 주요기능 (ul > li 목록)
        features = []
        ul = box.select_one(".sSol_cont > ul")
        if ul:
            features = [li.get_text(" ", strip=True) for li in ul.find_all("li")]

        # 특징: 여러 span으로 구성된 짧은 포인트들
        sol_char = []
        for span in box.select(".sSol_char .sSol_charRow span"):
            sol_char.append(span.get_text(" ", strip=True))

        # '프로그램 종류/적용분야/사용방법/OS' 같은 key-value 블록들
        ex_dict = {}
        for dl in box.select(".sSol_ex dl"):
            dt_tags = dl.find_all("dt")
            dd_tags = dl.find_all("dd")
            for dt, dd in zip(dt_tags, dd_tags):
                ex_dict[dt.get_text(strip=True)] = dd.get_text(" ", strip=True)

        # content 텍스트로 단일 합성
        content_lines = [
            desc,
            "주요기능: " + "; ".join(features) if features else "",
            "특징: " + "; ".join(sol_char) if sol_char else "",
            "; ".join([f"{k}: {v}" for k, v in ex_dict.items()]) if ex_dict else ""
        ]
        content = "\n".join([line for line in content_lines if line.strip()])

        items.append({
            "url": url,
            "section": "solution",
            "title": sol_name,      # 솔루션 이름
            "content": content.strip(),  # 솔루션 설명 통합
        })

    # 결과 저장 (append)
    with open(RAW_PATH, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f" ✔️[크롤러] 솔루션 {len(items)}개 저장 ({RAW_PATH})")

def crawl_business_pages():
    """
    비즈니스 페이지 묶음(/page/*.html)을 순회하며 요약 텍스트 수집.
    - 각 페이지에서 .cont 블록 아래의 소제목(h3 > small)과 첫 번째 문단(p)만 간단 수집
    - 결과는 section='business'로 저장

    참고:
    - 페이지별 텍스트 배치가 단순하다고 가정한 최소 스키마 크롤링.
    - 상세 문단까지 필요하면 선택자 확장.
    """
    ensure_dir(DATA_DIR)

    # /page/ 아래의 개별 비즈니스 페이지 파일명들
    business_pages = [
        "cloud.html",
        "infra.html",
        "outsourcing.html",
        "platform.html",
        "analysis.html",
        "portal.html",
        "dell.html"
    ]

    items = []
    for page in business_pages:
        url = BASE_URL + "page/" + page
        try:
            soup = fetch_soup(url)
            cont = soup.select_one(".cont")
            if cont:
                # 비즈니스명 (페이지 상단 소제목)
                biz_name_tag = cont.select_one("h3 > small")
                biz_name = biz_name_tag.get_text(strip=True) if biz_name_tag else ""

                # 설명(첫 번째 p) — 핵심 요약만 가져오기
                desc_tag = cont.find("p")
                desc = desc_tag.get_text(" ", strip=True) if desc_tag else ""

                items.append({
                    "url": url,
                    "section": "business",
                    "title": biz_name,
                    "content": desc
                })
        except Exception as e:
            # 페이지 구조 변경/네트워크 오류 등은 개별 페이지 단위로 보고만 하고 진행
            print(f"[ERROR] {page} ({url}) 크롤링 실패: {e}")

    # 결과 저장 (append)
    with open(RAW_PATH, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f" ✔️[크롤러] 비즈니스 {len(items)}개 저장 ({RAW_PATH})")

def crawl_all():
    """
    전체 크롤러 파이프라인 실행:
    1) 메인 페이지 섹션 수집
    2) 솔루션 상세 수집
    3) 비즈니스 요약 수집

    """
    crawl_main_page()
    crawl_solution_page()
    crawl_business_pages()
