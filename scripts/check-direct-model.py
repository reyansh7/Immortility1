"""Read-only Groq metadata, ONLY after separate account-metadata authorization.

No inference, account mutation, endpoint selection, retries or production activation.
"""

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/broker/src"))

import httpx
from immortility_broker.config import Settings
from immortility_broker.contracts import BrokerError
from immortility_broker.direct_metadata import groq_model_metadata
from immortility_broker.evidence import write_engineering_evidence
from immortility_broker.secrets import CredentialError, CredentialManager


async def main():
    settings = Settings()
    try:
        key = CredentialManager(provider="groq").read()
    except CredentialError:
        key = None
    key = key or settings.groq_api_key.get_secret_value()
    try:
        async with httpx.AsyncClient(
            trust_env=False, follow_redirects=False, transport=httpx.AsyncHTTPTransport(retries=0)
        ) as client:
            result = await groq_model_metadata(client, key)
    except BrokerError as error:
        result = {
            "status": "BLOCKED",
            "code": error.code,
            "model_requests": 0,
            "production_enabled": False,
        }
    output = write_engineering_evidence(result, "groq-model-metadata")
    print("Metadata evidence saved: " + str(output))
    print(
        "Production dispatch remains blocked; model listing does not prove Free-plan billing or quota."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--account-metadata-consent",
        action="store_true",
        help="Use only following separate explicit permission; sends one credential-backed official GET, zero model requests.",
    )
    if not parser.parse_args().account_metadata_consent:
        parser.error("Separate explicit account-metadata permission and its flag are required.")
    asyncio.run(main())
