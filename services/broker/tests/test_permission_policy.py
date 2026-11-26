"""The permission file is enforced. Unknown and powerful tools fail closed."""

from immortility_broker.permission_policy import decide, govern, load_policy


def test_shipped_read_tools_are_allowed_and_powerful_tools_are_denied():
    policy = load_policy()
    assert govern("project.read.v1", "observer", policy) == "allow"
    assert govern("clock.now.v1", "observer", policy) == "allow"
    assert govern("desktop.reveal.v1", "observer", policy) == "allow"
    assert govern("public.research.v1", "observer", policy) == "deny"
    assert govern("public.research.v1", "assisted", policy) == "allow"
    assert govern("report.create.v1", "assisted", policy) == "allow"
    for name in (
        "browser.navigate",
        "computer_use.click",
        "shell.exec",
        "yolo",
        "mcp.install",
        "unknown.tool",
    ):
        assert govern(name, "assisted", policy) == "deny"
        assert govern(name, "observer", policy) == "deny"


def test_global_approval_beats_an_allow_entry():
    policy = load_policy()
    profiles = policy["profiles"]
    assert isinstance(profiles, dict)
    assisted = profiles["assisted"]
    assert isinstance(assisted, dict)
    assisted["allow"] = frozenset(set(assisted["allow"]) | {"purchase"})
    assert decide(policy, "assisted", "purchase") == "approval"
    assert decide(policy, "observer", "not-a-real-action") == "deny"


def test_a_missing_policy_denies_every_capability(tmp_path):
    assert govern("clock.now.v1", "observer", {}) == "deny"
    missing = tmp_path / "absent.yaml"
    try:
        load_policy(missing)
    except OSError:
        denied = True
    else:
        denied = False
    assert denied
