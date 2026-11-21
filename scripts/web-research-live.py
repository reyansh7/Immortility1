"""Live check of the free web lookup (Wikipedia + DuckDuckGo Instant Answers).

Public, synthetic questions only; no broker data dir, no model. Writes JSON to argv[1]."""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "broker" / "src"))
from immortility_broker import web  # noqa: E402
from immortility_broker.contracts import BrokerError  # noqa: E402

QUESTIONS = [
    "search the web for Alan Turing",
    "look up the Rust programming language",
    "search the web for Pune",
    "web search photosynthesis",
    "search the web for xqzv-no-such-topic-2026",
]


async def main() -> None:
    # Optional owner contact for Wikimedia's User-Agent policy; without it only DuckDuckGo.
    contact = web.configure_contact(sys.argv[2]) if len(sys.argv) > 2 else False
    rows = [{"wikipedia_contact_configured": contact}]
    for question in QUESTIONS:
        t0 = time.perf_counter()
        try:
            page = await web.research_page_async(question)
            rows.append(
                {
                    "question": question,
                    "query_sent": page["query"],
                    "ms": round((time.perf_counter() - t0) * 1000),
                    "results": [
                        {
                            "source": s["source"],
                            "title": s["title"],
                            "url": s["url"],
                            "snippet_chars": len(s["snippet"]),
                        }
                        for s in page["sources"]
                    ],
                }
            )
        except BrokerError as error:
            rows.append(
                {
                    "question": question,
                    "error": error.code,
                    "ms": round((time.perf_counter() - t0) * 1000),
                }
            )
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    for row in rows[1:]:
        print(
            row["question"],
            "->",
            row.get("error") or [r["source"] + ":" + r["title"] for r in row["results"]],
            row["ms"],
            "ms",
        )


asyncio.run(main())
