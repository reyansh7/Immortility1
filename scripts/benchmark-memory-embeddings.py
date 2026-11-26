"""D23 benchmark: lexical v1 vs hybrid (local nomic-embed-text via Ollama loopback).

Synthetic memories only (no user data, no broker data dir); an in-memory SQLite database.
Measures recall@1 / recall@3 for direct and paraphrased questions, false recalls on
unrelated questions, cosine calibration and embedding latency. Writes JSON to argv[1].
"""

import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "broker" / "src"))
from immortility_broker import memory_embed  # noqa: E402
from immortility_broker.memory_embed import LoopbackEmbedder  # noqa: E402
from immortility_broker.memory_v1 import SEMANTIC_FLOOR, SEMANTIC_MIN, MemoryStore  # noqa: E402

MEMORIES = [
    ("profile", "My name is Arjun"),
    ("profile", "I live in Pune"),
    ("semantic", "I drive a grey Honda City"),
    ("semantic", "My dog is a beagle called Bruno"),
    ("profile", "I am vegetarian and do not eat eggs"),
    ("procedural", "I always run pytest before committing"),
    ("semantic", "The Immortility project is written in Rust and Python"),
    ("profile", "I prefer dark mode for editors"),
    ("semantic", "My sister Meera studies medicine in Manipal"),
    ("procedural", "Send me the daily summary at 9 pm"),
    ("semantic", "My laptop has an RTX 4060 graphics card"),
    ("profile", "I am allergic to penicillin"),
    ("semantic", "I play the tabla on weekends"),
    ("procedural", "Use metric units when you answer"),
    ("semantic", "My favourite cricket team is Mumbai Indians"),
]
# (question, index of the expected memory, kind)
QUERIES = [
    ("what is my name", 0, "direct"),
    ("where do I live", 1, "direct"),
    ("which dog do I have", 3, "direct"),
    ("what graphics card is in my laptop", 10, "direct"),
    ("which car do I own", 2, "paraphrase"),
    ("what vehicle is parked at my place", 2, "paraphrase"),
    ("what is my pet's breed", 3, "paraphrase"),
    ("can I have an omelette", 4, "paraphrase"),
    ("what food restrictions do I follow", 4, "paraphrase"),
    ("what should happen before I push code", 5, "paraphrase"),
    ("which programming languages does the assistant use", 6, "paraphrase"),
    ("what theme do I like in my IDE", 7, "paraphrase"),
    ("what is my sibling doing at university", 8, "paraphrase"),
    ("when do I want my evening report", 9, "paraphrase"),
    ("what GPU do I have", 10, "paraphrase"),
    ("which antibiotic should a doctor avoid giving me", 11, "paraphrase"),
    ("what musical instrument do I play", 12, "paraphrase"),
    ("should you use miles or kilometres", 13, "paraphrase"),
    ("which IPL side do I support", 14, "paraphrase"),
    ("which city am I based in", 1, "paraphrase"),
]
# Held out: written after the thresholds were chosen, never used to tune them.
HELD_OUT = [
    ("what do people call me", 0, "held_out"),
    ("what's the model of my car", 2, "held_out"),
    ("tell me about Bruno", 3, "held_out"),
    ("do I eat meat", 4, "held_out"),
    ("what is my brother or sister studying", 8, "held_out"),
    ("which medicines am I allergic to", 11, "held_out"),
    ("what do I do on Saturdays", 12, "held_out"),
    ("who do I cheer for in cricket", 14, "held_out"),
    ("what town is my home", 1, "held_out"),
    ("light or dark theme for coding", 7, "held_out"),
]
QUERIES = QUERIES + HELD_OUT
UNRELATED = [
    "what is the capital of Peru",
    "explain how photosynthesis works",
    "convert 5 dollars to rupees",
    "who wrote Hamlet",
    "what is the boiling point of water",
    "how tall is Mount Everest",
    "translate good morning into French",
    "what year did the Second World War end",
]


def build(embedder):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    store = MemoryStore(db, embedder)
    ids = [store.write(t, category=c, source="user")["id"] for c, t in MEMORIES]
    return store, ids


def evaluate(store, ids):
    rows = []
    for question, expected, kind in QUERIES:
        t0 = time.perf_counter()
        hits = store.search(question, limit=3, touch=False)
        ms = (time.perf_counter() - t0) * 1000
        got = [h["id"] for h in hits]
        rows.append(
            {
                "q": question,
                "kind": kind,
                "top1": bool(got) and got[0] == ids[expected],
                "top3": ids[expected] in got,
                "top_body": hits[0]["body"] if hits else None,
                "ms": round(ms, 1),
            }
        )
    false = []
    for question in UNRELATED:
        hits = store.search(question, limit=3, touch=False)
        false.append({"q": question, "recalled": [h["body"] for h in hits]})
    return rows, false


def summary(rows, false):
    out = {}
    for kind in ("direct", "paraphrase", "held_out"):
        sel = [r for r in rows if r["kind"] == kind]
        out[kind] = {
            "n": len(sel),
            "recall@1": sum(r["top1"] for r in sel),
            "recall@3": sum(r["top3"] for r in sel),
        }
    out["unrelated_with_any_recall"] = sum(1 for f in false if f["recalled"])
    out["search_ms_median"] = round(statistics.median(r["ms"] for r in rows), 1)
    return out


def main():
    model = sys.argv[2] if len(sys.argv) > 2 else "nomic-embed-text"
    lexical_store, lexical_ids = build(None)
    lex_rows, lex_false = evaluate(lexical_store, lexical_ids)

    probe = LoopbackEmbedder(model, timeout=60.0)
    t0 = time.perf_counter()
    warm = probe.embed(["warm up"])
    cold_ms = round((time.perf_counter() - t0) * 1000, 1)
    if warm is None:
        raise SystemExit("embedding model unavailable on loopback")
    lat = []
    for _ in range(10):
        t0 = time.perf_counter()
        probe.embed(["what car do I own"], query=True)
        lat.append((time.perf_counter() - t0) * 1000)
    # cosine calibration: expected pairs vs every other pair
    docs = probe.embed([t for _, t in MEMORIES])
    qs = probe.embed([q for q, _, _ in QUERIES], query=True)
    pos = [memory_embed.dot(qs[i], docs[e]) for i, (_, e, _) in enumerate(QUERIES)]
    neg = [
        memory_embed.dot(qs[i], docs[j])
        for i, (_, e, _) in enumerate(QUERIES)
        for j in range(len(MEMORIES))
        if j != e
    ]
    un = probe.embed(UNRELATED, query=True)
    un_max = [max(memory_embed.dot(u, d) for d in docs) for u in un]

    hybrid_store, hybrid_ids = build(LoopbackEmbedder(model, timeout=10.0))
    hybrid_store.ensure_vectors()
    hyb_rows, hyb_false = evaluate(hybrid_store, hybrid_ids)
    result = {
        "model": model,
        "dim": probe.dim,
        "endpoint": "loopback 127.0.0.1:11434 (fixed in code)",
        "data": "synthetic: 15 memories, 4 direct + 16 paraphrase (tuning) + 10 held-out questions, 8 unrelated",
        "embed_first_call_ms": cold_ms,
        "embed_query_ms": {
            "median": round(statistics.median(lat), 1),
            "max": round(max(lat), 1),
        },
        "cosine": {
            "expected_pairs": {
                "min": round(min(pos), 3),
                "median": round(statistics.median(pos), 3),
            },
            "other_pairs": {
                "median": round(statistics.median(neg), 3),
                "p95": round(sorted(neg)[int(len(neg) * 0.95)], 3),
                "max": round(max(neg), 3),
            },
            "unrelated_best": {"max": round(max(un_max), 3)},
            "floor": SEMANTIC_FLOOR,
            "min": SEMANTIC_MIN,
        },
        "lexical": summary(lex_rows, lex_false),
        "hybrid": summary(hyb_rows, hyb_false),
        "rows": {"lexical": lex_rows, "hybrid": hyb_rows},
        "unrelated": {"lexical": lex_false, "hybrid": hyb_false},
    }
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("embed_first_call_ms", "embed_query_ms", "cosine", "lexical", "hybrid")
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
