from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "backend" / "knowledge"
DATA_DIR = PROJECT_ROOT / "backend" / "data"
INDEX_PATH = DATA_DIR / "knowledge.index"
METADATA_PATH = DATA_DIR / "knowledge_metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"

load_dotenv(PROJECT_ROOT / "backend" / ".env")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "aegisdesk")
DYNAMIC_KNOWLEDGE_COLLECTION = "knowledge_dynamic"

_model: SentenceTransformer | None = None
_index: faiss.Index | None = None
_metadata: list[dict[str, Any]] = []


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Split an article into readable chunks while preferring paragraph boundaries."""
    paragraphs = [
        _clean_text(part)
        for part in re.split(r"\n\s*\n+", text)
        if _clean_text(part)
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars and not current:
            current = paragraph
            continue

        if current and len(current) + 1 + len(paragraph) <= max_chars:
            current = f"{current} {paragraph}"
            continue

        if current:
            chunks.append(current)

        if len(paragraph) <= max_chars:
            tail = current[-overlap:] if current else ""
            current = f"{tail} {paragraph}".strip() if tail else paragraph
            continue

        words = paragraph.split()
        piece = ""
        for word in words:
            candidate = f"{piece} {word}".strip()
            if len(candidate) > max_chars and piece:
                chunks.append(piece)
                tail_words = piece.split()[-20:]
                piece = " ".join(tail_words + [word])
            else:
                piece = candidate
        current = piece

    if current:
        chunks.append(current)

    return chunks


def _load_dynamic_articles() -> list[dict[str, Any]]:
    """Load published knowledge articles created by Knowledge Management Automation."""
    if not MONGODB_URI:
        return []

    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
        collection = client[MONGODB_DATABASE][DYNAMIC_KNOWLEDGE_COLLECTION]
        documents = collection.find(
            {"status": "published"},
            {"_id": 0},
        )
        articles: list[dict[str, Any]] = []
        for document in documents:
            articles.append(
                {
                    "id": document.get("article_id"),
                    "title": document.get("title", "Untitled Knowledge Article"),
                    "category": document.get("category", "General"),
                    "source": document.get("source", "AegisDesk Knowledge Management"),
                    "content": document.get("content", ""),
                }
            )
        client.close()
        return [article for article in articles if article.get("id") and article.get("content")]
    except PyMongoError:
        return []
    except Exception:
        return []


def _load_articles() -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            articles.extend(data)
        else:
            articles.append(data)

    articles.extend(_load_dynamic_articles())
    return articles


def _build_metadata() -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []

    for article in _load_articles():
        article_id = article["id"]
        title = article["title"]
        category = article.get("category", "General")
        source = article.get("source", title)
        body = article["content"]

        for index, chunk in enumerate(_chunk_text(body)):
            metadata.append(
                {
                    "chunk_id": f"{article_id}-chunk-{index + 1}",
                    "article_id": article_id,
                    "title": title,
                    "category": category,
                    "source": source,
                    "chunk_index": index,
                    "text": chunk,
                }
            )

    return metadata


def _get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def _build_index() -> None:
    global _index, _metadata

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _metadata = _build_metadata()

    if not _metadata:
        raise RuntimeError("No knowledge articles were found in backend/knowledge.")

    model = _get_model()
    embeddings = model.encode(
        [item["text"] for item in _metadata],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    _index = index

    faiss.write_index(index, str(INDEX_PATH))
    METADATA_PATH.write_text(
        json.dumps(_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_saved_index() -> None:
    global _index, _metadata

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        _build_index()
        return

    current_metadata = _build_metadata()
    saved_metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    # Rebuild automatically when knowledge documents change.
    current_signature = [(x["chunk_id"], x["text"]) for x in current_metadata]
    saved_signature = [(x["chunk_id"], x["text"]) for x in saved_metadata]

    if current_signature != saved_signature:
        _build_index()
        return

    _index = faiss.read_index(str(INDEX_PATH))
    _metadata = saved_metadata


def refresh_rag_index() -> dict[str, Any]:
    """Re-check static + MongoDB knowledge and rebuild the FAISS index if needed."""
    _load_saved_index()
    return {
        "status": "ready",
        "model": MODEL_NAME,
        "documents": len({item["article_id"] for item in _metadata}),
        "chunks": len(_metadata),
        "vector_dimension": _index.d if _index is not None else 0,
        "index": "FAISS IndexFlatIP",
    }


def ensure_rag_ready() -> dict[str, Any]:
    if _index is None:
        _load_saved_index()

    return {
        "status": "ready",
        "model": MODEL_NAME,
        "documents": len({item["article_id"] for item in _metadata}),
        "chunks": len(_metadata),
        "vector_dimension": _index.d if _index is not None else 0,
        "index": "FAISS IndexFlatIP",
    }


def search_knowledge(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    query = _clean_text(query)
    if not query:
        return []

    ensure_rag_ready()

    assert _index is not None
    model = _get_model()
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")

    scores, indices = _index.search(query_embedding, min(top_k, len(_metadata)))

    results: list[dict[str, Any]] = []
    for score, index_position in zip(scores[0], indices[0]):
        if index_position < 0:
            continue

        item = dict(_metadata[int(index_position)])
        similarity = float(score)
        item["similarity"] = round(similarity, 4)
        item["confidence"] = round(max(0.0, min(1.0, similarity)), 4)
        results.append(item)

    return results


def knowledge_articles() -> list[dict[str, Any]]:
    """Return one metadata record per approved knowledge article."""
    ensure_rag_ready()
    unique: dict[str, dict[str, Any]] = {}
    for item in _metadata:
        unique[item["article_id"]] = {
            "article_id": item["article_id"],
            "title": item["title"],
            "category": item["category"],
            "source": item["source"],
        }
    return sorted(unique.values(), key=lambda item: item["title"])


def rag_status() -> dict[str, Any]:
    ready = _index is not None
    if not ready:
        return {
            "status": "not_loaded",
            "model": MODEL_NAME,
            "documents": 0,
            "chunks": 0,
            "vector_dimension": 0,
            "index": "FAISS IndexFlatIP",
        }

    return {
        "status": "ready",
        "model": MODEL_NAME,
        "documents": len({item["article_id"] for item in _metadata}),
        "chunks": len(_metadata),
        "vector_dimension": _index.d if _index is not None else 0,
        "index": "FAISS IndexFlatIP",
    }
