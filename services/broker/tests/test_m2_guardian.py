"""PC Guardian: read-only Defender status (M2)."""

import pytest

from immortility_broker.permission_policy import govern
from immortility_broker.storage_audit import defender_status, intent


@pytest.mark.parametrize(
    "text",
    ["Is Defender on?", "check my antivirus status", "show security status", "PC Guardian status"],
)
def test_security_questions_route_to_the_read_only_tool(text):
    assert intent(text) == ("laptop.security.v1", {})


def test_unrelated_text_does_not_route():
    assert intent("write a poem about a defender of the castle") is None
    assert intent("what is antimatter") is None


def test_healthy_and_problem_reports():
    healthy = defender_status(
        lambda: {
            "AntivirusEnabled": True,
            "RealTimeProtectionEnabled": True,
            "IsTamperProtected": True,
            "AntivirusSignatureAge": 0,
            "QuickScanAge": 2,
            "FullScanAge": 40,
        }
    )
    assert "Looks healthy" in healthy and "nothing was changed" in healthy
    assert "today" in healthy and "2 days ago" in healthy
    bad = defender_status(
        lambda: {
            "AntivirusEnabled": True,
            "RealTimeProtectionEnabled": False,
            "AntivirusSignatureAge": 9,
        }
    )
    assert "real-time protection" in bad and "definitions are old" in bad
    assert "unavailable" not in bad
    assert "not available" in defender_status(lambda: {})


def test_policy_allows_the_read_only_check_only():
    assert govern("laptop.security.v1", "observer") == "allow"
    assert govern("laptop.security.disable.v1", "observer") == "deny"
