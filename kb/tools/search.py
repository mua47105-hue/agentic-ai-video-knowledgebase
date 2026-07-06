#!/usr/bin/env python3
"""
Hybrid search CLI over wiki markdown files.
Uses BM25 (via rank_bm25 if available, fallback to simple TF) + optional vector reranking.

Usage:
    python3 search.py "query terms"                    # simple TF search
    python3 search.py "query terms" --vector           # + vector rerank (requires sentence-transformers)
    python3 search.py "query terms" --top-k 5          # top 5 results
    python3 search.py "query terms" --page preview     # show page preview
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple

WIKI_DIR = Path(__file__).resolve().parent.parent / "wiki"


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def load_documents() -> List[Tuple[str, str, str]]:
    """Return list of (path, title, content) for all .md files under wiki."""
    docs = []
    for fpath in sorted(WIKI_DIR.rglob("*.md")):
        if fpath.name.startswith("_"):
            continue
        rel = str(fpath.relative_to(WIKI_DIR))
        content = fpath.read_text(encoding="utf-8")
        title = fpath.stem.replace("-", " ").title()
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if m:
            title = m.group(1).strip()
        docs.append((rel, title, content))
    return docs


def compute_tf_scores(docs: List[Tuple[str, str, str]], query_terms: List[str]) -> List[float]:
    scores = []
    for _, _, content in docs:
        tokens = tokenize(content)
        tf = Counter(tokens)
        score = sum(tf.get(q, 0) for q in query_terms)
        scores.append(score)
    return scores


def compute_bm25_scores(
    docs: List[Tuple[str, str, str]], query_terms: List[str], k1: float = 1.5, b: float = 0.75
) -> List[float]:
    N = len(docs)
    doc_token_lists = [tokenize(content) for _, _, content in docs]
    avg_dl = sum(len(t) for t in doc_token_lists) / max(N, 1)

    idf_cache = {}
    for qt in set(query_terms):
        df = sum(1 for tl in doc_token_lists if qt in tl)
        idf_cache[qt] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

    scores = []
    for tokens in doc_token_lists:
        dl = len(tokens)
        tf = Counter(tokens)
        score = 0.0
        for qt in query_terms:
            f = tf.get(qt, 0)
            score += idf_cache[qt] * ((f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avg_dl)))
        scores.append(score)
    return scores


def vector_rerank(
    docs: List[Tuple[str, str, str]], query: str, top_k: int
) -> List[Tuple[str, str, float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("vector rerank requires sentence-transformers: pip install sentence-transformers", file=sys.stderr)
        return []

    model = SentenceTransformer("all-MiniLM-L6-v2")
    contents = [content for _, _, content in docs]
    emb_docs = model.encode(contents, normalize_embeddings=True)
    emb_query = model.encode(query, normalize_embeddings=True)
    scores = (emb_docs @ emb_query).tolist()
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in indexed[:top_k]:
        rel, title, _ = docs[idx]
        results.append((rel, title, score))
    return results


def highlight(text: str, query_terms: List[str]) -> str:
    for qt in query_terms:
        text = re.sub(
            f"(?i)({re.escape(qt)})",
            lambda m: f"\033[1;33m{m.group(1)}\033[0m",
            text,
        )
    return text


def main():
    parser = argparse.ArgumentParser(description="Search the AI video editing wiki")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    parser.add_argument("--vector", action="store_true", help="Use vector reranking")
    parser.add_argument("--algo", choices=["tf", "bm25"], default="bm25", help="Base ranking algorithm")
    parser.add_argument("--page", type=str, help="View a specific wiki page (relative path)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.page:
        fpath = WIKI_DIR / args.page
        if not fpath.exists():
            print(f"Page not found: {fpath}", file=sys.stderr)
            sys.exit(1)
        print(fpath.read_text(encoding="utf-8"))
        return

    docs = load_documents()
    if not docs:
        print("No wiki pages found.", file=sys.stderr)
        sys.exit(1)

    query_terms = tokenize(args.query)
    if not query_terms:
        print("No searchable terms in query.", file=sys.stderr)
        sys.exit(1)

    # Base ranking
    if args.algo == "tf":
        scores = compute_tf_scores(docs, query_terms)
    else:
        scores = compute_bm25_scores(docs, query_terms)

    indexed = [(i, s) for i, s in enumerate(scores)]
    indexed.sort(key=lambda x: x[1], reverse=True)
    top = indexed[: args.top_k * 3]  # keep more for vector rerank

    # Vector rerank
    if args.vector:
        reranked = vector_rerank([docs[i] for i, _ in top], args.query, args.top_k)
        if reranked:
            if args.json:
                print(json.dumps(reranked, indent=2))
            else:
                print(f"\n=== Search: '{args.query}' (BM25 + vector) ===\n")
                for rel, title, score in reranked:
                    print(f"  [{score:.3f}] {title}")
                    print(f"         kb/wiki/{rel}")
                    print()
            return

    # Fallback / BM25-only output
    results = []
    for rank, (idx, score) in enumerate(top[: args.top_k]):
        if score <= 0:
            continue
        rel, title, content = docs[idx]
        results.append((rel, title, score))

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(f"\n=== Search: '{args.query}' ({args.algo.upper()}) ===\n")
    if not results:
        print("  No results.")
        return

    for rel, title, score in results:
        print(f"  [{score:.3f}] {title}")
        print(f"         kb/wiki/{rel}")

    print()


if __name__ == "__main__":
    main()
