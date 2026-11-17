"""Long-chat fitting, verified identity, and project-answer grounding."""

from immortility_broker.dialogue import (
    asks_identity,
    ground_project_answer,
    identity_text,
    prepare_history,
)


def test_one_hundred_messages_keep_the_latest_question_inside_a_budget():
    history = []
    for index in range(100):
        history.append({"role": "user", "content": f"question {index} " + ("x" * 400)})
        history.append({"role": "assistant", "content": f"answer {index} " + ("y" * 800)})
    fitted = prepare_history(history)
    assert sum(len(item["content"]) for item in fitted) < 4500
    assert any("question 99" in item["content"] for item in fitted)
    assert not any(item["content"].startswith("question 0 ") for item in fitted)
    assert asks_identity("What model are you?")


def test_identity_names_the_verified_route_and_rejects_the_invented_persona():
    text = identity_text("groq", "openai/gpt-oss-120b")
    assert "openai/gpt-oss-120b" in text
    assert "nvidia/nemotron-3-ultra-550b-a55b" in text
    assert "gemini-3.5-flash" in text
    assert "I am not Particle-1" in text
    assert "was not created by Particle AI" in text


def test_project_answer_drops_electron_and_invented_entry_points():
    evidence = "pytest pyproject.toml services/broker apps/desktop Tauri"
    answer = (
        "The desktop is Electron. The entry point is agents/immortality.py. "
        "Start it with uvicorn services.broker.src:app. Tests use pytest from pyproject.toml."
    )
    grounded = ground_project_answer(answer, evidence)
    assert "Electron" not in grounded
    assert "immortality.py" not in grounded
    assert "uvicorn" not in grounded
    assert "pytest" in grounded
    assert "pyproject.toml" in grounded
    assert "Unverified claims were removed" in grounded
