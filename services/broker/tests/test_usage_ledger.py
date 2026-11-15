import concurrent.futures
import sqlite3

import pytest

from immortility_broker.contracts import BrokerError
from immortility_broker.ledger import Ledger


def ledger(path):
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return Ledger(db)


def test_reservations_are_atomic_across_concurrent_calls_and_attempts(tmp_path):
    usage = ledger(tmp_path / "usage.db")
    attempts = [usage.begin("task", 1000, 2, "free") for _ in range(2)]

    def reserve(index):
        try:
            return usage.reserve(attempts[index % 2], 200, 300)
        except BrokerError as error:
            return error.code

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(reserve, range(16)))
    assert results.count("budget_exhausted") == 14
    assert usage.summary("task")["charged_tokens"] == 1000
    usage.db.close()


def test_unknown_usage_survives_restart_and_cannot_be_refunded_twice(tmp_path):
    path = tmp_path / "usage.db"
    usage = ledger(path)
    attempt = usage.begin("task", 1000, 4, "free")
    call = usage.reserve(attempt, 200, 300)
    usage.settle(call, None)
    usage.db.close()
    usage = ledger(path)
    assert usage.summary("task") == {
        "calls": 1,
        "dispatch_attempts": 1,
        "not_sent_calls": 0,
        "pending_reservations": 0,
        "charged_tokens": 500,
        "unknown_calls": 1,
        "prompt_tokens": None,
        "completion_tokens": None,
    }
    with pytest.raises(BrokerError, match="usage_conflict"):
        usage.settle(call, {"prompt_tokens": 0, "completion_tokens": 0})
    other = usage.begin("foreign", 1000, 2, "free")
    usage.reserve(other, 500, 500)
    usage.db.close()


def test_usage_refunds_unused_tokens_and_records_cache_reasoning_without_double_counting(tmp_path):
    usage = ledger(tmp_path / "usage.db")
    attempt = usage.begin("task", 1000, 4, "free")
    first = usage.reserve(attempt, 200, 300)
    usage.settle(
        first,
        {
            "prompt_tokens": 100,
            "completion_tokens": 100,
            "prompt_tokens_details": {"cached_tokens": 70},
            "completion_tokens_details": {"reasoning_tokens": 60},
        },
    )
    second = usage.reserve(attempt, 400, 400)
    usage.settle(second, None, sent=False)
    assert usage.summary("task")["charged_tokens"] == 200
    assert usage.summary("task")["unknown_calls"] == 0
    usage.db.close()


@pytest.mark.parametrize(
    "reported",
    [
        {"prompt_tokens": True, "completion_tokens": 0},
        {"prompt_tokens": -1, "completion_tokens": 1},
        {},
    ],
)
def test_invalid_usage_keeps_the_full_reservation(tmp_path, reported):
    usage = ledger(tmp_path / "usage.db")
    call = usage.reserve(usage.begin("task", 1000, 2, "free"), 200, 300)
    usage.settle(call, reported)
    assert usage.summary("task")["charged_tokens"] == 500
    usage.db.close()


def test_overrun_persists_and_blocks_following_attempts(tmp_path):
    usage = ledger(tmp_path / "usage.db")
    call = usage.reserve(usage.begin("task", 1000, 4, "free"), 100, 100)
    with pytest.raises(BrokerError, match="usage_overrun"):
        usage.settle(call, {"prompt_tokens": 101, "completion_tokens": 1})
    with pytest.raises(BrokerError, match="usage_overrun"):
        usage.reserve(usage.begin("task", 1000, 4, "free"), 1, 1)
    assert usage.summary("task")["charged_tokens"] == 102
    usage.db.close()
