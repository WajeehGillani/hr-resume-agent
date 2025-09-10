# src/tools/retriever.py
from __future__ import annotations
import os, csv, json, time, hashlib
from typing import List, Dict, Optional
from pathlib import Path

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from src.state import JD


EMBED_MODEL = "text-embedding-3-small"
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FAISS_DIR = ARTIFACTS_DIR / "faiss_qbank"
FAISS_DIR.mkdir(parents=True, exist_ok=True)


def _csv_mtime(path: str) -> float:
    return os.path.getmtime(path)


def _sha256_text(txt: str) -> str:
    h = hashlib.sha256(); h.update(txt.encode("utf-8", errors="ignore")); return h.hexdigest()


def _offline_embed(texts: List[str]) -> np.ndarray:
    DIM = 1536
    vecs: List[np.ndarray] = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8", errors="ignore")).digest()
        seed = int.from_bytes(h[:4], byteorder="big", signed=False)
        rng = np.random.RandomState(seed)
        v = rng.normal(loc=0.0, scale=1.0, size=(DIM,)).astype(np.float32)
        n = np.linalg.norm(v) + 1e-9
        vecs.append(v / n)
    return np.stack(vecs, axis=0)


class LocalQuestionBank:
    """
    Loads role/question pairs, builds a FAISS vector store, and searches by similarity.
    Uses OpenAI embeddings if available (OPENAI_API_KEY), otherwise a deterministic offline embedding with FAISS.
    """

    def __init__(self, csv_path: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing question bank CSV: {csv_path}")
        self.csv_path = csv_path
        self.rows: List[Dict[str, str]] = self._load_csv(csv_path)
        self.corpus: List[str] = [f"{r['role']} :: {r['question']}" for r in self.rows]
        self.index_path = FAISS_DIR / "index"
        self.meta_path = FAISS_DIR / "meta.json"
        self._ensure_index()

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

    def _online_embeddings(self) -> Optional[OpenAIEmbeddings]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return OpenAIEmbeddings(model=EMBED_MODEL)

    def _cache_valid(self) -> bool:
        if not (self.index_path.exists() and self.meta_path.exists()):
            return False
        try:
            meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            if meta.get("model") != EMBED_MODEL:
                return False
            if float(meta.get("csv_mtime", 0)) != _csv_mtime(self.csv_path):
                return False
            if meta.get("rows") != len(self.corpus):
                return False
            if meta.get("corpus_sha256") != _sha256_text("\n".join(self.corpus)):
                return False
            return True
        except Exception:
            return False

    def _ensure_index(self) -> None:
        if self._cache_valid():
            try:
                self.vs = FAISS.load_local(str(self.index_path), self._online_embeddings() or None, allow_dangerous_deserialization=True)
                return
            except Exception:
                pass
        # (Re)build
        os.makedirs(str(self.index_path), exist_ok=True)
        embs = self._online_embeddings()
        if embs is not None:
            # Build with online embeddings
            self.vs = FAISS.from_texts(self.corpus, embedding=embs)
        else:
            # Offline deterministic vectors using FAISS manual index
            import faiss  # type: ignore
            vecs = _offline_embed(self.corpus)
            index = faiss.IndexFlatIP(vecs.shape[1])
            index.add(vecs)
            # store mapping to original texts
            self.vs = FAISS(embedding_function=lambda x: _offline_embed(x), index=index, docstore={}, index_to_docstore_id={})
            # populate docstore
            for i, txt in enumerate(self.corpus):
                self.vs.docstore[str(i)] = txt  # type: ignore[attr-defined]
                self.vs.index_to_docstore_id[i] = str(i)  # type: ignore[attr-defined]

        # Save and meta
        self.vs.save_local(str(self.index_path))
        meta = {
            "model": EMBED_MODEL,
            "csv_mtime": _csv_mtime(self.csv_path),
            "rows": len(self.corpus),
            "corpus_sha256": _sha256_text("\n".join(self.corpus)),
            "built_at": time.time(),
        }
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def search(self, query: str, top_k: int = 10) -> List[str]:
        if not getattr(self, "vs", None):
            return []
        try:
            docs = self.vs.similarity_search(query, k=top_k)
            return [getattr(d, "page_content", str(d)) for d in docs]
        except Exception:
            # Offline manual sim as last resort
            vecs = _offline_embed(self.corpus)
            q = _offline_embed([query])
            sims = (vecs @ q.T)[..., 0]
            idx = np.argsort(-sims)[:top_k]
            return [self.corpus[i].split("::", 1)[-1].strip() for i in idx]


def build_query_from_jd(jd: JD) -> str:
    title = jd.title.strip() if jd.title else "Role"
    must = ", ".join([s.strip() for s in jd.must_haves if s.strip()]) if jd.must_haves else ""
    return f"{title} :: {must}"

