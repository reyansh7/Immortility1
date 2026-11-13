from immortility_broker.memory import prior_task_notes, retrieve, trim_history


def test_retrieve_keeps_the_matching_paragraph_only():
    text = "Alpha has nothing useful.\nThe broker stores task notes locally."
    selected = retrieve(text, "where are task notes stored")
    assert "task notes" in selected
    assert "Alpha" not in selected


def test_trim_history_keeps_the_newest_messages():
    history = [
        {"role": "user", "content": "old " * 20},
        {"role": "assistant", "content": "older"},
        {"role": "user", "content": "keep this"},
    ]
    trimmed = trim_history(history, 12)
    assert trimmed[-1]["content"] == "keep this"
    assert "old" not in "".join(item["content"] for item in trimmed)


def test_prior_notes_ignore_unrelated_tasks():
    tasks = [
        {
            "task_id": "1",
            "status": "succeeded",
            "input": {"content": "python length function"},
            "result": {"text": "Use len."},
        },
        {
            "task_id": "2",
            "status": "succeeded",
            "input": {"content": "bake a cake"},
            "result": {"text": "Use flour."},
        },
    ]
    notes = prior_task_notes(tasks, "python string length", "3")
    assert "len" in notes
    assert "flour" not in notes
