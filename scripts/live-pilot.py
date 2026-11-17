"""Live desktop pilot. Refuses to run until quota evidence and an explicit opt-in exist.

No provider call is made by this script in its current state. Missing account
quota is not treated as permission to spend a free-tier request.
"""

import json
import sys

BLOCK = {
    "status": "blocked",
    "inference_category": "live_model",
    "calls_made": 0,
    "reason": (
        "Groq, Gemini, and NVIDIA do not expose a remaining-balance API that this "
        "broker can read. A missing rate-limit header is not remaining quota. "
        "The 3-5 task pilot stays prepared and unrun."
    ),
    "required_to_unblock": [
        "Confirm the account plan in the provider console.",
        "Set IMMORTILITY_LIVE_PILOT=authorized for one explicit run.",
        "Keep the call cap at or below 5 and do not retry on quota errors.",
    ],
}


def main() -> int:
    print(json.dumps(BLOCK, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
