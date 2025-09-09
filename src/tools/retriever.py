# src/tools/retriever.py
from __future__ import annotations
import os, csv, json, time, hashlib
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from openai import OpenAI
from src.state import JD


EMBED_MODEL = "text-embedding-3-small"
CACHE_VEC = "artifacts/qbank.npy"
CACHE_META = "artifacts/qbank_meta.json"


from pathlib import Path

EMBED_MODEL = "text-embedding-3-small"

# Anchor caches to the repo root /artifacts, regardless of where you run Python
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CACHE_VEC = str(ARTIFACTS_DIR / "qbank.npy")
CACHE_META = str(ARTIFACTS_DIR / "qbank_meta.json")


def _client() -> Optional[OpenAI]:
    """Return OpenAI client if API key is available, else None for offline fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    return None

def _expected_dim() -> int:
    # OpenAI text-embedding-3-small uses 1536 dimensions
    return 1536

def _csv_mtime(path: str) -> float:
    return os.path.getmtime(path)

def _sha256_text(txt: str) -> str:
    h = hashlib.sha256(); h.update(txt.encode("utf-8", errors="ignore")); return h.hexdigest()

def embed_texts(texts: List[str]) -> np.ndarray:
    """Return shape (N, D) embeddings.

    Falls back to deterministic, offline embeddings when no API key is set.
    """
    client = _client()
    if client is None:
        # Offline deterministic embedding using hash-seeded random vectors
        # Use 1536 to match OpenAI text-embedding-3-small dimensionality
        DIM = 1536
        vecs: List[np.ndarray] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8", errors="ignore")).digest()
            # Use 32-bit seed to satisfy NumPy RandomState requirements
            seed = int.from_bytes(h[:4], byteorder="big", signed=False)
            rng = np.random.RandomState(seed)
            v = rng.normal(loc=0.0, scale=1.0, size=(DIM,)).astype(np.float32)
            # normalize
            n = np.linalg.norm(v) + 1e-9
            vecs.append(v / n)
        return np.stack(vecs, axis=0)

    # Online embedding via OpenAI
    BATCH = 128
    out: List[List[float]] = []
    for i in range(0, len(texts), BATCH):
        chunk = texts[i:i+BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=chunk)
        out.extend([d.embedding for d in resp.data])
    return np.array(out, dtype=np.float32)

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_n = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_n = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_n @ b_n.T  # (N, M)

class LocalQuestionBank:
    """
    Loads role/question pairs, builds an embedding cache, and searches by cosine similarity.
    Cache is invalidated if the CSV changes or model changes.
    """

    def __init__(self, csv_path: str, cache_vec: str = CACHE_VEC, cache_meta: str = CACHE_META):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing question bank CSV: {csv_path}")
        self.csv_path = csv_path
        self.cache_vec = cache_vec
        self.cache_meta = cache_meta
        self.rows: List[Dict[str, str]] = self._load_csv(csv_path)
        self.corpus: List[str] = [f"{r['role']} :: {r['question']}" for r in self.rows]
        self.emb: np.ndarray | None = None
        self._ensure_embeddings()

    def _load_csv(self, path: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                role = (r.get("role") or "").strip()
                q = (r.get("question") or "").strip()
                if role and q:
                    rows.append({"role": role, "question": q})
        if not rows:
            raise ValueError("Question bank is empty. Add rows to data/question_bank.csv")
        return rows

    def _cache_valid(self) -> bool:
        if not (os.path.exists(self.cache_vec) and os.path.exists(self.cache_meta)):
            return False
        try:
            with open(self.cache_meta, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("model") != EMBED_MODEL:
                return False
            if float(meta.get("csv_mtime", 0)) != _csv_mtime(self.csv_path):
                return False
            if meta.get("rows") != len(self.corpus):
                return False
            if meta.get("corpus_sha256") != _sha256_text("\n".join(self.corpus)):
                return False
            # Ensure embedding dimension matches expected
            if int(meta.get("dim", 0)) != _expected_dim():
                return False
            return True
        except Exception:
            return False

    def _ensure_embeddings(self) -> None:
        if self._cache_valid():
            self.emb = np.load(self.cache_vec)
            return
        # (Re)build
        os.makedirs(os.path.dirname(self.cache_vec), exist_ok=True)
        self.emb = embed_texts(self.corpus)
        np.save(self.cache_vec, self.emb)
        meta = {
            "model": EMBED_MODEL,
            "csv_mtime": _csv_mtime(self.csv_path),
            "rows": len(self.corpus),
            "corpus_sha256": _sha256_text("\n".join(self.corpus)),
            "dim": int(self.emb.shape[1]) if self.emb is not None and self.emb.ndim == 2 else 0,
            "built_at": time.time(),
        }
        with open(self.cache_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def search(self, query: str, top_k: int = 10) -> List[str]:
        if self.emb is None or self.emb.shape[0] == 0:
            return []
        q_vec = embed_texts([query])  # (1, D)
        sims = _cosine_sim(self.emb, q_vec)[..., 0]  # (N,)
        idx = np.argsort(-sims)[:top_k]
        return [self.rows[i]["question"] for i in idx]


def build_query_from_jd(jd: JD) -> str:
    title = jd.title.strip() if jd.title else "Role"
    must = ", ".join([s.strip() for s in jd.must_haves if s.strip()]) if jd.must_haves else ""
    return f"{title} :: {must}"

