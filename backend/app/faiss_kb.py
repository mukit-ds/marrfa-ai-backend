# backend/app/faiss_kb.py
import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai

load_dotenv()


class MarrfaFaissKB:
    def __init__(self, out_dir: str | None = None):
        # ✅ SINGLE SOURCE OF TRUTH FOR PATH
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.out_dir = out_dir or os.path.join(base_dir, "Knowledge", "marrfa_kb_out")

        self.index_path = os.path.join(self.out_dir, "kb.index")
        self.meta_path = os.path.join(self.out_dir, "metadata.pkl")
        self.ids_path = os.path.join(self.out_dir, "ids.json")
        self.chunks_path = os.path.join(self.out_dir, "chunks.jsonl")

        self.index = None
        self.chunk_by_id: Dict[str, Dict[str, Any]] = {}
        self.ids: List[str] = []
        self.enabled = False

        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.client = openai.OpenAI(api_key=api_key) if api_key else None

        self._load_or_fallback()

    # ---------------- LOADERS ---------------- #

    def _load_or_fallback(self):
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
                self._load_legacy()
                self.enabled = True
                print(f"✅ FAISS KB loaded from {self.out_dir}")
                return

            if os.path.exists(self.index_path) and os.path.exists(self.chunks_path):
                self._load_new()
                self.enabled = True
                print(f"✅ FAISS KB (new format) loaded from {self.out_dir}")
                return

            raise FileNotFoundError("FAISS KB files not found")

        except Exception as e:
            print(f"⚠️ FAISS KB load failed: {e}")
            self._create_fallback()
            self.enabled = True

    def _load_legacy(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            self.chunk_by_id = pickle.load(f)

    def _load_new(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.ids_path, "r") as f:
            self.ids = json.load(f)
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                self.chunk_by_id[c["id"]] = c

    # ---------------- FALLBACK ---------------- #

    def _create_fallback(self):
        print("⚠️ Using fallback company KB")
        self.chunk_by_id = {
            "about": {
                "title": "About Marrfa",
                "content": "Marrfa Real Estate is a Dubai-based real estate company offering residential and commercial property services.",
            },
            "leadership": {
                "title": "Leadership",
                "content": "Marrfa is led by an experienced executive team responsible for strategic growth and operations in Dubai.",
            },
        }

    # ---------------- EMBEDDINGS ---------------- #

    def _embed(self, text: str) -> np.ndarray:
        if not self.client:
            return np.random.randn(1, 1536).astype("float32")

        try:
            res = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return np.array(res.data[0].embedding, dtype="float32").reshape(1, -1)
        except Exception:
            return np.random.randn(1, 1536).astype("float32")

    # ---------------- QUERY ---------------- #

    def query(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.index:
            return list(self.chunk_by_id.values())

        q_emb = self._embed(query_text)
        D, I = self.index.search(q_emb, top_k)

        results = []
        for idx in I[0]:
            if idx < 0:
                continue
            cid = self.ids[idx] if self.ids and idx < len(self.ids) else list(self.chunk_by_id.keys())[idx]
            if cid in self.chunk_by_id:
                results.append(self.chunk_by_id[cid])

        return results

    # ---------------- ANSWER ---------------- #

    def answer(self, query_text: str, top_k: int = 12) -> str:
        q = query_text.lower()
        chunks = self.query(query_text, top_k=top_k)

        # CEO / OWNER GUARANTEE
        if any(x in q for x in ["ceo", "owner", "founder"]):
            for c in chunks:
                if "ceo" in c.get("content", "").lower() or "lead" in c.get("title", "").lower():
                    return c["content"]

        if chunks:
            return chunks[0].get("content", "")

        return ""
