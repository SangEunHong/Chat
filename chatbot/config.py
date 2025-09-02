# config.py
from pathlib import Path

BASE_URL = "https://www.bumil.co.kr/"
BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"
SFT_DIR = BASE_DIR / "sft"
MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"

# raw/clean/chunk jsonl 경로
RAW_PATH = DATA_DIR / "raw.jsonl"
CLEAN_PATH = DATA_DIR / "clean.jsonl"
CHUNKS_PATH = DATA_DIR / "chunks.jsonl"

# FAISS 인덱스/메타/텍스트
FAISS_INDEX = INDEX_DIR / "faiss_ip.index"
FAISS_METAS = INDEX_DIR / "metas.jsonl"
FAISS_TEXTS = INDEX_DIR / "texts.jsonl"

# config.py (추가)
GEN_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"   # 또는 1.5B 권장
GEN_MAX_TOKENS = 512
GEN_TEMPERATURE = 0.7
GEN_TOP_P = 0.9

# LoRA 적용 시 (선택)
SFT_MODEL_DIR = MODELS_DIR / "qwen25-0_5b-lora"   # 새로 지정

# 임베딩/QA 모델명
EMBED_MODEL_NAME = "BAAI/bge-m3"


# 윈도우/리눅스 모두 호환 경로로 관리!
